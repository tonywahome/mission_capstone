from database import get_admin_client
import uuid

db = get_admin_client()

# Get Orpheus's user ID
user_result = db.table('users').select('id').eq('email', 'o.manga@alustudent.com').execute()
user_id = user_result.data[0]['id']
print(f'User ID: {user_id}')

# Get the pending credit
credit_result = db.table('carbon_credits').select('*, scan_results(*)').eq('owner_id', user_id).eq('status', 'pending_approval').execute()
if credit_result.data:
    credit = credit_result.data[0]
    
    # Create notification
    notification = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'type': 'scan_complete',
        'title': 'Land Scan Complete - Review Results',
        'message': f'Your land scan has been completed. Review the findings: {credit["quantity_tco2e"]:.2f} tCO2e. Please review and approve to list on marketplace.',
        'read': False,
        'data': {
            'scan_id': credit['scan_id'],
            'credit_id': credit['id'],
            'plot_id': credit['plot_id'],
            'tco2e': credit['quantity_tco2e'],
            'price_per_tonne': credit.get('price_per_tonne', 15.0),
            'integrity_score': credit.get('integrity_score', 65),
            'risk_score': credit.get('risk_score', 0.35) * 100,
        }
    }
    
    result = db.table('notifications').insert(notification).execute()
    print(f'✅ Created notification: {notification["id"]}')
    print(f'   Message: {notification["message"]}')
else:
    print('❌ No pending credits found')
