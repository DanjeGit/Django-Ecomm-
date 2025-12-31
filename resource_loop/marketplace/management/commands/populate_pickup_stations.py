from django.core.management.base import BaseCommand
from marketplace.models import PickupStation
from marketplace.locations import KENYA_LOCATIONS

class Command(BaseCommand):
    help = 'Populates the database with sample pickup stations'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating pickup stations...')

        # Add Nairobi manually since it might be missing in locations.py
        nairobi_subcounties = ["Westlands", "Dagoretti North", "Dagoretti South", "Langata", "Kibra", "Roysambu", "Kasarani", "Ruaraka", "Embakasi South", "Embakasi North", "Embakasi Central", "Embakasi East", "Embakasi West", "Makadara", "Kamukunji", "Starehe", "Mathare"]
        
        stations_data = [
            # Nairobi
            {"name": "G4S Westlands", "county": "Nairobi", "sub_county": "Westlands", "address": "Westlands Square, Ground Floor"},
            {"name": "Wells Fargo CBD", "county": "Nairobi", "sub_county": "Starehe", "address": "City Centre, Moi Avenue"},
            {"name": "Posta City Square", "county": "Nairobi", "sub_county": "Starehe", "address": "Haile Selassie Ave"},
            {"name": "G4S Karen", "county": "Nairobi", "sub_county": "Langata", "address": "Karen Shopping Centre"},
            {"name": "Wells Fargo Industrial Area", "county": "Nairobi", "sub_county": "Makadara", "address": "Enterprise Road"},
            
            # Mombasa
            {"name": "G4S Mombasa CBD", "county": "Mombasa", "sub_county": "Mvita", "address": "Nkrumah Road"},
            {"name": "Wells Fargo Nyali", "county": "Mombasa", "sub_county": "Nyali", "address": "Nyali Centre"},
            
            # Kisumu
            {"name": "G4S Kisumu", "county": "Kisumu", "sub_county": "Kisumu Central", "address": "Oginga Odinga Street"},
            
            # Nakuru
            {"name": "G4S Nakuru", "county": "Nakuru", "sub_county": "Nakuru Town East", "address": "Kenyatta Avenue"},
            
            # Kiambu
            {"name": "G4S Thika", "county": "Kiambu", "sub_county": "Thika Town", "address": "Thika Arcade"},
            {"name": "Wells Fargo Ruiru", "county": "Kiambu", "sub_county": "Ruiru", "address": "Ruiru Town"},
            
            # Uasin Gishu
            {"name": "G4S Eldoret", "county": "Uasin Gishu", "sub_county": "Turbo", "address": "Oloo Street"},
        ]

        # Add generic stations for other locations in KENYA_LOCATIONS
        # Just adding one per sub-county for demonstration if needed, but let's stick to the curated list above for quality.
        # However, to ensure coverage, let's add a generic "Town Centre Pickup" for the first sub-county of each county.
        
        for county, sub_counties in KENYA_LOCATIONS.items():
            if sub_counties:
                sc = sub_counties[0]
                stations_data.append({
                    "name": f"{county} Town Pickup Point",
                    "county": county,
                    "sub_county": sc,
                    "address": f"Main Bus Stage, {sc}"
                })

        count = 0
        for station in stations_data:
            obj, created = PickupStation.objects.get_or_create(
                name=station['name'],
                county=station['county'],
                sub_county=station['sub_county'],
                defaults={'address': station['address']}
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} pickup stations.'))
