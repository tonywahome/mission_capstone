EMISSION_FACTORS = {
    # --- Scope 2: Purchased electricity ---
    "electricity_kwh": 0.000027,   # tCO2e per kWh (Rwanda grid average, MININFRA 2023 — ~90% hydro)

    # --- Scope 1: Direct fuel combustion ---
    "diesel_litre": 0.002676,      # tCO2e per litre (IPCC 2006 Tier 1)
    "petrol_litre": 0.002315,      # tCO2e per litre
    "natural_gas_litre": 0.002020, # kept for fuel_type=natural_gas compat
    "lpg_kg": 0.002983,            # tCO2e per kg

    # --- Scope 1: Natural gas heating (dedicated field) ---
    "natural_gas_heating_m3": 0.002020,  # tCO2e per m³ (IPCC 2006, ~2.02 kg CO2e/m³)

    # --- Scope 1: Refrigerant leakage ---
    # Default: R-410A (GWP=2088, most common commercial HVAC refrigerant)
    "refrigerant_r410a_kg": 2.088,       # tCO2e per kg leaked

    # --- Scope 3: Business air travel ---
    "flight_km_short": 0.000255,   # tCO2e per km (< 1500 km, economy class, DEFRA 2023)
    "flight_km_long": 0.000195,    # tCO2e per km (> 1500 km, with radiative forcing)

    # --- Scope 3: Waste ---
    "waste_landfill_kg": 0.000465, # tCO2e per kg to landfill (DEFRA 2023)
    "waste_recycled_kg": 0.000021, # tCO2e per kg recycled

    # --- Scope 3: Water ---
    "water_m3": 0.000344,          # tCO2e per m³ (treatment + supply)

    # --- Scope 3: Freight ---
    "freight_truck_tonne_km": 0.000062,  # tCO2e per tonne-km (road, average truck)
    "freight_ship_tonne_km": 0.000011,   # tCO2e per tonne-km (container ship, DEFRA)

    # --- Scope 3: Supply chain (spend-based, USEEIO average) ---
    "supply_chain_spend_usd": 0.000308,  # tCO2e per USD spent (EPA USEEIO industry avg)
}

# Carbon Credit Pricing (USD per tonne CO2e)
# Based on 2024-2026 voluntary carbon market rates for nature-based solutions in East Africa
BASE_PRICE_PER_TONNE = 5.00  # USD - Market average for forestry/conservation credits
PREMIUM_PRICE = 8.00  # High-integrity, verified conservation projects
STANDARD_PRICE = 4.00  # Standard conservation credits
MINIMUM_PRICE = 2.00  # Entry-level credits

# Community benefit allocation (% of credit sale going to local communities)
COMMUNITY_BENEFIT_PERCENTAGE = 0.60  # 60% goes directly to communities


def calculate_footprint(
    # Scope 2
    energy_kwh_monthly: float = 0,
    # Scope 1 - fuel combustion
    fuel_litres_monthly: float = 0,
    fuel_type: str = "diesel",
    # Scope 1 - natural gas heating
    natural_gas_m3_monthly: float = 0,
    # Scope 1 - refrigerant leakage
    refrigerant_leaked_kg_annual: float = 0,
    # Scope 3 - flights
    flights_short_km_annual: float = 0,
    flights_long_km_annual: float = 0,
    # Scope 3 - waste
    waste_landfill_kg_monthly: float = 0,
    waste_recycled_kg_monthly: float = 0,
    # Scope 3 - water
    water_m3_monthly: float = 0,
    # Scope 3 - freight
    freight_tonne_km_monthly: float = 0,
    freight_sea_tonne_km_monthly: float = 0,
    # Scope 3 - supply chain (spend-based)
    supply_chain_spend_usd_monthly: float = 0,
) -> dict:
    """Calculate carbon footprint from multiple sources, structured by GHG Protocol scopes."""

    # --- Scope 2: Purchased electricity ---
    electricity_emissions = energy_kwh_monthly * 12 * EMISSION_FACTORS["electricity_kwh"]

    # --- Scope 1: Fuel combustion ---
    fuel_key = f"{fuel_type}_litre"
    fuel_factor = EMISSION_FACTORS.get(fuel_key, EMISSION_FACTORS["diesel_litre"])
    fuel_emissions = fuel_litres_monthly * 12 * fuel_factor

    # --- Scope 1: Natural gas heating ---
    natural_gas_emissions = natural_gas_m3_monthly * 12 * EMISSION_FACTORS["natural_gas_heating_m3"]

    # --- Scope 1: Refrigerant leakage (annual input) ---
    refrigerant_emissions = refrigerant_leaked_kg_annual * EMISSION_FACTORS["refrigerant_r410a_kg"]

    # --- Scope 3: Business flights (annual input) ---
    flights_emissions = (
        flights_short_km_annual * EMISSION_FACTORS["flight_km_short"]
        + flights_long_km_annual * EMISSION_FACTORS["flight_km_long"]
    )

    # --- Scope 3: Waste ---
    waste_emissions = (
        waste_landfill_kg_monthly * 12 * EMISSION_FACTORS["waste_landfill_kg"]
        + waste_recycled_kg_monthly * 12 * EMISSION_FACTORS["waste_recycled_kg"]
    )

    # --- Scope 3: Water ---
    water_emissions = water_m3_monthly * 12 * EMISSION_FACTORS["water_m3"]

    # --- Scope 3: Road freight ---
    freight_road_emissions = freight_tonne_km_monthly * 12 * EMISSION_FACTORS["freight_truck_tonne_km"]

    # --- Scope 3: Sea freight ---
    freight_sea_emissions = freight_sea_tonne_km_monthly * 12 * EMISSION_FACTORS["freight_ship_tonne_km"]

    # --- Scope 3: Supply chain spend-based ---
    supply_chain_emissions = supply_chain_spend_usd_monthly * 12 * EMISSION_FACTORS["supply_chain_spend_usd"]

    # Scope aggregates
    scope1_total = fuel_emissions + natural_gas_emissions + refrigerant_emissions
    scope2_total = electricity_emissions
    scope3_total = (
        flights_emissions + waste_emissions + water_emissions
        + freight_road_emissions + freight_sea_emissions + supply_chain_emissions
    )
    total = scope1_total + scope2_total + scope3_total

    return {
        "annual_tco2e": round(total, 2),
        "monthly_tco2e": round(total / 12, 2),
        # Scope totals
        "scope1_tco2e": round(scope1_total, 2),
        "scope2_tco2e": round(scope2_total, 2),
        "scope3_tco2e": round(scope3_total, 2),
        # Individual sources
        "electricity_tco2e": round(electricity_emissions, 2),
        "fuel_tco2e": round(fuel_emissions, 2),
        "natural_gas_tco2e": round(natural_gas_emissions, 2),
        "refrigerant_tco2e": round(refrigerant_emissions, 2),
        "flights_tco2e": round(flights_emissions, 2),
        "waste_tco2e": round(waste_emissions, 2),
        "water_tco2e": round(water_emissions, 2),
        "freight_tco2e": round(freight_road_emissions, 2),
        "freight_sea_tco2e": round(freight_sea_emissions, 2),
        "supply_chain_tco2e": round(supply_chain_emissions, 2),
        "breakdown": {
            "electricity": round(electricity_emissions, 2),
            "fuel": round(fuel_emissions, 2),
            "natural_gas": round(natural_gas_emissions, 2),
            "refrigerant": round(refrigerant_emissions, 2),
            "flights": round(flights_emissions, 2),
            "waste": round(waste_emissions, 2),
            "water": round(water_emissions, 2),
            "freight_road": round(freight_road_emissions, 2),
            "freight_sea": round(freight_sea_emissions, 2),
            "supply_chain": round(supply_chain_emissions, 2),
        },
    }


def calculate_credit_price(integrity_score: float, risk_score: float) -> float:
    """
    Calculate carbon credit price based on quality metrics.
    
    Pricing tiers:
    - Premium (90-100 integrity, <0.15 risk): $30-40/tonne
    - High Quality (75-89 integrity, 0.15-0.30 risk): $22-30/tonne  
    - Standard (60-74 integrity, 0.30-0.45 risk): $15-22/tonne
    - Basic (<60 integrity, >0.45 risk): $10-15/tonne
    
    Args:
        integrity_score: 0-100 score (higher = better monitoring/verification)
        risk_score: 0-1 score (higher = more risk)
    
    Returns:
        Price per tonne in USD
    """
    # Determine base price tier
    if integrity_score >= 90 and risk_score < 0.15:
        base = PREMIUM_PRICE
    elif integrity_score >= 75 and risk_score < 0.30:
        base = BASE_PRICE_PER_TONNE
    elif integrity_score >= 60 and risk_score < 0.45:
        base = STANDARD_PRICE
    else:
        base = MINIMUM_PRICE
    
    # Fine-tune within tier
    integrity_bonus = (integrity_score - 50) / 100 * 8  # +/- $4 based on integrity
    risk_penalty = risk_score * 10  # Up to -$10 for high risk
    
    adjusted_price = base + integrity_bonus - risk_penalty
    
    # Enforce minimum viable price for communities
    adjusted_price = max(adjusted_price, MINIMUM_PRICE)
    
    return round(adjusted_price, 2)


def calculate_community_benefit(credit_value: float) -> dict:
    """
    Calculate how much goes to local communities.
    
    Args:
        credit_value: Total value of carbon credit in USD
        
    Returns:
        Dict with community benefit breakdown
    """
    community_share = credit_value * COMMUNITY_BENEFIT_PERCENTAGE
    platform_fee = credit_value * 0.15  # 15% platform/verification costs
    conservation_fund = credit_value * 0.25  # 25% to ongoing conservation activities
    
    return {
        "community_direct": round(community_share, 2),
        "conservation_fund": round(conservation_fund, 2),
        "platform_fee": round(platform_fee, 2),
        "community_percentage": COMMUNITY_BENEFIT_PERCENTAGE * 100,
    }
