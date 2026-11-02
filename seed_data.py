"""
Optional sample data seeder for Scout Sandou2 Treasury.
Run this script anytime to insert initial representative data for testing.
"""
from datetime import date
import database

def seed():
    database.init_db()
    
    # Check if records already exist
    existing = database.get_transactions()
    if existing:
        print(f"Database already contains {len(existing)} transactions. Skipping seed to prevent duplicates.")
        return

    sample_transactions = [
        # USD Incomes
        {
            'type_': 'income',
            'amount': 350.0,
            'currency': 'USD',
            'party_or_purpose': 'Troop Sponsor - Al-Amal Community',
            'category': 'Sponsorship',
            'notes': 'Quarterly youth development grant',
            'date': '2026-10-02'
        },
        {
            'type_': 'income',
            'amount': 120.0,
            'currency': 'USD',
            'party_or_purpose': 'Scout Alumni Association Donation',
            'category': 'Donation',
            'notes': 'Contributed towards camping gear',
            'date': '2026-10-15'
        },
        # LBP Incomes
        {
            'type_': 'income',
            'amount': 15000000.0,
            'currency': 'LBP',
            'party_or_purpose': 'Troop Membership Dues (اشتراكات كشفية)',
            'category': 'Monthly Dues',
            'notes': 'Monthly subscription collected from patrols',
            'date': '2026-10-05'
        },
        {
            'type_': 'income',
            'amount': 4500000.0,
            'currency': 'LBP',
            'party_or_purpose': 'Bake Sale Fundraiser (ريع نشاط خيري)',
            'category': 'Fundraiser',
            'notes': 'Scout bakery stall proceeds',
            'date': '2026-10-18'
        },
        # USD Expenses
        {
            'type_': 'expense',
            'amount': 95.0,
            'currency': 'USD',
            'party_or_purpose': 'Camping Tents & Pioneer Ropes',
            'category': 'Camping Equipment',
            'notes': 'Heavy duty 100m rope & groundsheets',
            'date': '2026-10-09'
        },
        {
            'type_': 'expense',
            'amount': 60.0,
            'currency': 'USD',
            'party_or_purpose': 'First Aid Kit Restock & Medical Supplies',
            'category': 'General',
            'notes': 'Bandages, antiseptic, thermal blankets',
            'date': '2026-10-20'
        },
        # LBP Expenses
        {
            'type_': 'expense',
            'amount': 3800000.0,
            'currency': 'LBP',
            'party_or_purpose': 'Snacks, Water & Fruit for Nature Hike',
            'category': 'Food & Snacks',
            'notes': 'Provisions for 35 scout attendees',
            'date': '2026-10-11'
        },
        {
            'type_': 'expense',
            'amount': 2200000.0,
            'currency': 'LBP',
            'party_or_purpose': 'Printing Rank Advancement Books & Badges',
            'category': 'Printing & Badges',
            'notes': 'Scout progress tracking logs',
            'date': '2026-10-24'
        }
    ]

    for t in sample_transactions:
        database.add_transaction(**t)

    print(f"Successfully seeded {len(sample_transactions)} sample transactions into scout_finance.db!")

if __name__ == '__main__':
    seed()
