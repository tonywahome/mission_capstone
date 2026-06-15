"""
Create sample carbon credits for the marketplace with realistic data.
This script generates diverse credits from different regions and quality tiers.
"""
import uuid
from datetime import datetime
from database import get_supabase_client
from services.carbon_calculator import calculate_credit_price, calculate_community_benefit

# Sample conservation projects across Kenya
SAMPLE_PROJECTS = [
    {
        "plot_name": "Aberdare Forest Conservation",
        "region": "Nyeri County",
        "area_ha": 45.3,
        "biomass_tonnes_ha": 180.5,
        "integrity_score": 92.4,
        "risk_score": 0.12,
        "vintage_year": 2024,
        "description": "Old-growth forest protection in Aberdare ecosystem"
    },
    {
        "plot_name": "Mount Kenya Woodland Restoration",
        "region": "Meru County",
        "area_ha": 28.7,
        "biomass_tonnes_ha": 125.3,
        "integrity_score": 88.1,
        "risk_score": 0.18,
        "vintage_year": 2024,
        "description": "Active reforestation of degraded highland areas"
    },
    {
        "plot_name": "Kakamega Rainforest Buffer",
        "region": "Kakamega County",
        "area_ha": 67.2,
        "biomass_tonnes_ha": 210.8,
        "integrity_score": 94.7,
        "risk_score": 0.08,
        "vintage_year": 2024,
        "description": "Indigenous rainforest preservation project"
    },
    {
        "plot_name": "Mau Forest Rehabilitation",
        "region": "Nakuru County",
        "area_ha": 52.1,
        "biomass_tonnes_ha": 95.4,
        "integrity_score": 76.3,
        "risk_score": 0.28,
        "vintage_year": 2024,
        "description": "Community-led forest restoration initiative"
    },
    {
        "plot_name": "Loita Forest Conservation",
        "region": "Narok County",
        "area_ha": 38.9,
        "biomass_tonnes_ha": 142.7,
        "integrity_score": 85.2,
        "risk_score": 0.22,
        "vintage_year": 2024,
        "description": "Maasai community forest stewardship program"
    },
    {
        "plot_name": "Taita Hills Agroforestry",
        "region": "Taita-Taveta County",
        "area_ha": 22.4,
        "biomass_tonnes_ha": 68.9,
        "integrity_score": 72.6,
        "risk_score": 0.35,
        "vintage_year": 2024,
        "description": "Mixed farming with conservation trees"
    },
    {
        "plot_name": "Karura Forest Extension",
        "region": "Nairobi County",
        "area_ha": 18.3,
        "biomass_tonnes_ha": 98.2,
        "integrity_score": 81.4,
        "risk_score": 0.25,
        "vintage_year": 2024,
        "description": "Urban forest conservation and expansion"
    },
    {
        "plot_name": "Arabuko-Sokoke Eco Project",
        "region": "Kilifi County",
        "area_ha": 43.7,
        "biomass_tonnes_ha": 156.3,
        "integrity_score": 89.8,
        "risk_score": 0.16,
        "vintage_year": 2024,
        "description": "Coastal forest biodiversity protection"
    },
]

def create_sample_credits():
    """Generate sample carbon credits for demonstration."""
    db = get_supabase_client()
    
    print("🌳 Creating sample carbon credits for marketplace...\n")
    
    created_credits = []
    
    for project in SAMPLE_PROJECTS:
        # Calculate carbon sequestration
        # Formula: Biomass (t/ha) × 0.47 (carbon fraction) × 3.667 (CO2 factor) × Area
        biomass_total = project["biomass_tonnes_ha"] * project["area_ha"]
        tco2e = biomass_total * 0.47 * 3.667
        
        # Calculate price based on quality
        price_per_tonne = calculate_credit_price(
            project["integrity_score"],
            project["risk_score"]
        )
        
        # Calculate community benefit
        total_value = price_per_tonne * tco2e
        community_benefit = calculate_community_benefit(total_value)
        
        # Create credit record
        credit_id = str(uuid.uuid4())
        credit_data = {
            "id": credit_id,
            "plot_id": str(uuid.uuid4()),  # Generate dummy plot ID
            "plot_name": project["plot_name"],
            "region": project["region"],
            "quantity_tco2e": round(tco2e, 2),
            "price_per_tonne": price_per_tonne,
            "integrity_score": project["integrity_score"],
            "risk_score": project["risk_score"],
            "vintage_year": project["vintage_year"],
            "status": "listed",  # Make them immediately available
            "listed_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        try:
            result = db.table("carbon_credits").insert(credit_data).execute()
            created_credits.append(credit_data)
            
            print(f"✅ Created: {project['plot_name']}")
            print(f"   Location: {project['region']}")
            print(f"   Carbon: {tco2e:.1f} tCO2e")
            print(f"   Price: ${price_per_tonne}/tonne (Total: ${total_value:.2f})")
            print(f"   Community Benefit: ${community_benefit['community_direct']:.2f}")
            print(f"   Quality: Integrity {project['integrity_score']:.1f}, Risk {project['risk_score']:.2f}")
            print()
            
        except Exception as e:
            print(f"❌ Failed to create {project['plot_name']}: {e}")
    
    print(f"\n🎉 Successfully created {len(created_credits)} carbon credits!")
    print(f"\nMarket Summary:")
    total_carbon = sum(c["quantity_tco2e"] for c in created_credits)
    total_value = sum(c["price_per_tonne"] * c["quantity_tco2e"] for c in created_credits)
    avg_price = sum(c["price_per_tonne"] for c in created_credits) / len(created_credits)
    
    print(f"  Total Carbon Available: {total_carbon:.0f} tCO2e")
    print(f"  Total Market Value: ${total_value:.2f}")
    print(f"  Average Price: ${avg_price:.2f} per tonne")
    print(f"  Community Impact Fund: ${total_value * 0.6:.2f} (60%)")
    print(f"\n🌐 Visit http://localhost:3001/marketplace to see the credits!")

if __name__ == "__main__":
    try:
        create_sample_credits()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Backend server is running")
        print("  2. Database is configured")
        print("  3. Run from backend directory: python create_sample_credits.py")
