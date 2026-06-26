from supabase import create_client, Client
from config import settings
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# In-memory database fallback when Supabase is not configured
class InMemoryDB:
    """Simple in-memory database for demo purposes when Supabase is not configured."""
    
    def __init__(self):
        self.data = {
            "carbon_credits": [],
            "scan_results": [],
            "land_plots": [],
            "transactions": [],
            "audit_log": [],
            "users": [],
            "sessions": [],
        }
        self._initialized = False
    
    def table(self, table_name: str):
        """Get a table-like interface."""
        return InMemoryTable(self.data, table_name)
    
    def initialize_sample_data(self):
        """Initialize with sample carbon credits.

        This fallback fires whenever Supabase isn't configured/reachable
        (see get_supabase_client()/get_admin_client() below), so it's live,
        active code, not a dormant script. The project list below was
        Kenya-region demo data (Aberdare/Nyeri, Mount Kenya/Meru, Kakamega,
        Mau/Nakuru, Loita/Narok) predating the Rwanda/Bugesera-Rulindo
        re-scope; replaced with the same five Bugesera/Rulindo plots used in
        backend/data/sample_data.sql for consistency across the demo data
        the app can fall back to. Status uses 'pending_approval' (the
        rescoped verification-queue value — see routers/scan.py) rather
        than the legacy marketplace 'listed' status this used to write.
        """
        if self._initialized:
            return

        from services.carbon_calculator import calculate_credit_price

        sample_projects = [
            {
                "id": "aaaaaaaa-0001-0000-0000-000000000000",
                "plot_name": "Nyamata Grassland",
                "region": "Bugesera, Rwanda",
                "area_ha": 45.3,
                "biomass_tonnes_ha": 38.5,
                "integrity_score": 81.4,
                "risk_score": 0.22,
                "vintage_year": 2026,
            },
            {
                "id": "aaaaaaaa-0002-0000-0000-000000000000",
                "plot_name": "Ngenda Savanna",
                "region": "Bugesera, Rwanda",
                "area_ha": 28.7,
                "biomass_tonnes_ha": 42.1,
                "integrity_score": 79.6,
                "risk_score": 0.25,
                "vintage_year": 2026,
            },
            {
                "id": "aaaaaaaa-0003-0000-0000-000000000000",
                "plot_name": "Gashora Wetland",
                "region": "Bugesera, Rwanda",
                "area_ha": 19.4,
                "biomass_tonnes_ha": 55.8,
                "integrity_score": 74.2,
                "risk_score": 0.31,
                "vintage_year": 2026,
            },
            {
                "id": "aaaaaaaa-0004-0000-0000-000000000000",
                "plot_name": "Base Agroforestry",
                "region": "Rulindo, Rwanda",
                "area_ha": 52.1,
                "biomass_tonnes_ha": 88.4,
                "integrity_score": 90.1,
                "risk_score": 0.14,
                "vintage_year": 2026,
            },
            {
                "id": "aaaaaaaa-0005-0000-0000-000000000000",
                "plot_name": "Buyoga Agroforestry",
                "region": "Rulindo, Rwanda",
                "area_ha": 38.9,
                "biomass_tonnes_ha": 95.7,
                "integrity_score": 92.8,
                "risk_score": 0.11,
                "vintage_year": 2026,
            },
        ]

        for project in sample_projects:
            biomass_total = project["biomass_tonnes_ha"] * project["area_ha"]
            tco2e = biomass_total * 0.47 * 3.667
            price = calculate_credit_price(project["integrity_score"], project["risk_score"])

            credit = {
                "id": project["id"],
                "plot_id": project["id"],  # reuse same stable ID
                "owner_id": "00000000-0000-0000-0000-000000000000",  # demo steward
                "plot_name": project["plot_name"],
                "region": project["region"],
                "quantity_tco2e": round(tco2e, 2),
                "price_per_tonne": price,
                "integrity_score": project["integrity_score"],
                "risk_score": project["risk_score"],
                "vintage_year": project["vintage_year"],
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
            }
            self.data["carbon_credits"].append(credit)

        self._initialized = True
        logger.info(f"Initialized in-memory DB with {len(sample_projects)} sample credits")


class InMemoryTable:
    """Mimics Supabase table interface for in-memory storage."""

    def __init__(self, data: Dict, table_name: str):
        self.data = data
        self.table_name = table_name
        self.query = {}
        self.order_by_field = None
        self.order_desc = False
        self._pending_insert = None
        self._pending_delete = False
        self._pending_update = None
        # Auto-create table if it doesn't exist
        if table_name not in self.data:
            self.data[table_name] = []

    @staticmethod
    def _result(rows):
        return type('obj', (object,), {'data': rows})()

    def select(self, fields: str = "*"):
        self._pending_insert = None
        self._pending_delete = False
        self._pending_update = None
        self.query = {}
        return self

    def eq(self, field: str, value: Any):
        self.query[field] = value
        return self

    def gte(self, field: str, value: Any):
        self.query[f"{field}__gte"] = value
        return self

    def order(self, field: str, desc: bool = False):
        self.order_by_field = field
        self.order_desc = desc
        return self

    def insert(self, data):
        self._pending_insert = data
        return self

    def update(self, data: Dict):
        self._pending_update = data
        return self

    def delete(self):
        self._pending_delete = True
        return self

    def execute(self):
        """Execute the pending operation and return results."""
        table = self.data[self.table_name]

        # INSERT
        if self._pending_insert is not None:
            payload = self._pending_insert
            if isinstance(payload, list):
                for item in payload:
                    table.append(item)
                return self._result(payload)
            else:
                table.append(payload)
                return self._result([payload])

        # DELETE
        if self._pending_delete:
            removed = []
            remaining = []
            for record in table:
                if self._matches(record):
                    removed.append(record)
                else:
                    remaining.append(record)
            self.data[self.table_name] = remaining
            return self._result(removed)

        # UPDATE
        if self._pending_update is not None:
            updated = []
            for i, record in enumerate(table):
                if self._matches(record):
                    table[i].update(self._pending_update)
                    updated.append(table[i])
            return self._result(updated)

        # SELECT (default)
        results = list(table)
        for key, value in self.query.items():
            if "__gte" in key:
                field = key.replace("__gte", "")
                results = [r for r in results if r.get(field, 0) >= value]
            else:
                results = [r for r in results if r.get(key) == value]

        if self.order_by_field:
            results.sort(
                key=lambda x: x.get(self.order_by_field, ""),
                reverse=self.order_desc,
            )

        return self._result(results)

    def _matches(self, record: Dict) -> bool:
        for key, value in self.query.items():
            if "__gte" in key:
                field = key.replace("__gte", "")
                if record.get(field, 0) < value:
                    return False
            else:
                if record.get(key) != value:
                    return False
        return True


# Global in-memory database instance
_in_memory_db = InMemoryDB()


# Cache the Supabase client to avoid creating it on every request
_supabase_client = None
_client_initialized = False

def get_supabase_client() -> Client:
    """Get Supabase client or fall back to in-memory database."""
    global _supabase_client, _client_initialized
    
    if _client_initialized:
        return _supabase_client
    
    _client_initialized = True

    try:
        # Try to create Supabase client
        print(f"[DB] Attempting Supabase connection to {settings.supabase_url}")

        if settings.supabase_url and settings.supabase_anon_key and settings.supabase_url != "your-project-url":
            client = create_client(settings.supabase_url, settings.supabase_anon_key)
            # Verify the tables exist with a test query
            try:
                client.table("carbon_credits").select("id").limit(1).execute()
                _supabase_client = client
                print(f"[DB] Connected to Supabase: {settings.supabase_url}")
                logger.info(f"Connected to Supabase: {settings.supabase_url}")
                return _supabase_client
            except Exception as table_err:
                print(f"[DB] Supabase tables not found. Run backend/data/schema.sql in Supabase SQL editor.")
                print(f"[DB] https://app.supabase.com/project/mozrcszdqinkjnnopkio/sql/new")
                logger.warning(f"Supabase tables missing ({table_err}), falling back to in-memory database")
        else:
            print("[DB] Supabase credentials not configured, using in-memory database")
            logger.warning("Supabase credentials not properly configured")
    except Exception as e:
        print(f"[DB] Supabase connection failed: {e}")
        logger.warning(f"Supabase connection failed, using in-memory database: {e}")

    # Fall back to in-memory database
    print("[DB] Using in-memory database with sample data")
    logger.info("Using in-memory database with sample data (Supabase not configured)")
    _in_memory_db.initialize_sample_data()
    _supabase_client = _in_memory_db
    return _supabase_client


def get_admin_client() -> Client:
    """Get admin client or fall back to in-memory database."""
    try:
        if settings.supabase_url and settings.supabase_service_role_key and settings.supabase_url != "your-project-url":
            client = create_client(settings.supabase_url, settings.supabase_service_role_key)
            logger.info("Connected to Supabase with admin privileges")
            return client
    except Exception as e:
        logger.warning(f"Supabase admin connection failed: {e}")
    
    logger.info("Using in-memory database (Supabase not configured)")
    _in_memory_db.initialize_sample_data()
    return _in_memory_db
