#!/usr/bin/env python3
"""
Update Carbon Credit Prices - Migration Script
Recalculates prices for all existing carbon credits using new pricing structure

Run this script from the backend directory:
    python data/recalculate_prices.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase_client
from services.carbon_calculator import calculate_credit_price
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection
db = get_supabase_client()


def recalculate_all_prices():
    """Recalculate prices for all carbon credits in the database."""
    
    try:
        # Fetch all carbon credits
        response = db.table('carbon_credits').select('*').execute()
        
        if not response.data:
            logger.warning("No carbon credits found in database")
            return
        
        credits = response.data
        logger.info(f"Found {len(credits)} carbon credits to update")
        
        updated_count = 0
        total_old_value = 0
        total_new_value = 0
        
        for credit in credits:
            credit_id = credit['id']
            integrity_score = credit.get('integrity_score', 70)
            risk_score = credit.get('risk_score', 0.25)
            quantity = credit.get('quantity_tco2e', 0)
            old_price = credit.get('price_per_tonne', 0)
            
            # Calculate new price using updated pricing structure
            new_price = calculate_credit_price(integrity_score, risk_score)
            
            old_value = old_price * quantity
            new_value = new_price * quantity
            
            total_old_value += old_value
            total_new_value += new_value
            
            # Update the database
            update_response = db.table('carbon_credits')\
                .update({'price_per_tonne': new_price})\
                .eq('id', credit_id)\
                .execute()
            
            if update_response.data:
                updated_count += 1
                logger.info(
                    f"✓ Updated credit {credit_id[:8]}: "
                    f"${old_price:.2f} → ${new_price:.2f} per tonne "
                    f"(value: ${old_value:.2f} → ${new_value:.2f})"
                )
            else:
                logger.error(f"✗ Failed to update credit {credit_id[:8]}")
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("PRICE UPDATE SUMMARY")
        logger.info("="*70)
        logger.info(f"Total credits updated: {updated_count}/{len(credits)}")
        logger.info(f"Total portfolio value:")
        logger.info(f"  Before: ${total_old_value:,.2f}")
        logger.info(f"  After:  ${total_new_value:,.2f}")
        logger.info(f"  Change: ${total_new_value - total_old_value:,.2f} "
                   f"({((total_new_value/total_old_value - 1) * 100):.1f}%)")
        logger.info("="*70)
        
        return {
            'updated_count': updated_count,
            'total_credits': len(credits),
            'old_value': total_old_value,
            'new_value': total_new_value
        }
        
    except Exception as e:
        logger.error(f"Error recalculating prices: {e}", exc_info=True)
        return None


def preview_changes():
    """Preview what changes would be made without updating the database."""
    
    try:
        response = db.table('carbon_credits').select('*').execute()
        
        if not response.data:
            logger.warning("No carbon credits found in database")
            return
        
        credits = response.data
        logger.info(f"\nPREVIEW: Changes for {len(credits)} carbon credits\n")
        logger.info("-" * 100)
        logger.info(f"{'ID':<10} {'Quantity':<12} {'Old Price':<12} {'New Price':<12} {'Old Value':<12} {'New Value':<12} {'Change':<10}")
        logger.info("-" * 100)
        
        total_old_value = 0
        total_new_value = 0
        
        for credit in credits:
            integrity_score = credit.get('integrity_score', 70)
            risk_score = credit.get('risk_score', 0.25)
            quantity = credit.get('quantity_tco2e', 0)
            old_price = credit.get('price_per_tonne', 0)
            
            new_price = calculate_credit_price(integrity_score, risk_score)
            
            old_value = old_price * quantity
            new_value = new_price * quantity
            
            total_old_value += old_value
            total_new_value += new_value
            
            change_pct = ((new_value / old_value - 1) * 100) if old_value > 0 else 0
            
            logger.info(
                f"{credit['id'][:8]:<10} "
                f"{quantity:<12.2f} "
                f"${old_price:<11.2f} "
                f"${new_price:<11.2f} "
                f"${old_value:<11.2f} "
                f"${new_value:<11.2f} "
                f"{change_pct:>9.1f}%"
            )
        
        logger.info("-" * 100)
        logger.info(f"{'TOTAL':<10} {'':<12} {'':<12} {'':<12} "
                   f"${total_old_value:<11,.2f} ${total_new_value:<11,.2f} "
                   f"{((total_new_value/total_old_value - 1) * 100):>9.1f}%")
        logger.info("-" * 100)
        
    except Exception as e:
        logger.error(f"Error previewing changes: {e}", exc_info=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Recalculate carbon credit prices')
    parser.add_argument('--preview', action='store_true', 
                       help='Preview changes without updating database')
    parser.add_argument('--execute', action='store_true',
                       help='Execute the price updates')
    
    args = parser.parse_args()
    
    if args.preview:
        logger.info("Running in PREVIEW mode - no changes will be made")
        preview_changes()
    elif args.execute:
        logger.info("Running in EXECUTE mode - updating database...")
        confirm = input("\nThis will update ALL carbon credit prices. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            result = recalculate_all_prices()
            if result:
                logger.info("\n✓ Price update completed successfully")
        else:
            logger.info("Update cancelled")
    else:
        logger.info("Usage:")
        logger.info("  python data/recalculate_prices.py --preview    # Preview changes")
        logger.info("  python data/recalculate_prices.py --execute    # Update prices")
