from hubspot import HubSpot
from hubspot.crm.deals import ApiException
from urllib3.util.retry import Retry
from config import Config
import os,simplejson



# Initialize the HubSpot client with retry logic
class Functions:
    """
    Import Hubspot functions
    // Blog posts imported
    """

    def process_deal(deal,hubspot_client):
        deal_dict = deal.to_dict()

        try:
            contacts_page = hubspot_client.crm.associations.v4.basic_api.get_page(
                'deals', deal.id, 'contacts')
            contact_ids = [result.to_object_id for result in contacts_page.results]

            companies_page = hubspot_client.crm.associations.v4.basic_api.get_page(
                'deals', deal.id, 'companies')
            company_ids = [result.to_object_id for result in companies_page.results]

            owner_email = None
            if deal.properties.get('hubspot_owner_id'):
                try:
                    owner = hubspot_client.crm.owners.owners_api.get_by_id(
                        owner_id=deal.properties['hubspot_owner_id'],
                        id_property='id',
                        archived=False)
                    owner_email = owner.properties.get('email')
                except ApiException as e:
                    print(f"Exception when fetching owner details: {e}\n")

            contacts_batch = hubspot_client.crm.contacts.batch_api.read(
                batch_read_input_simple_public_object_id={
                    "properties": ['email', 'firstname', 'lastname'],
                    "inputs": [
                    {
                        "id": id
                    } for id in contact_ids
                    ]
                }) if contact_ids else None

            companies_batch = hubspot_client.crm.companies.batch_api.read(
                batch_read_input_simple_public_object_id={
                    "properties": ['name', 'domain', 'hs_additional_domains', 'website'],
                    "inputs": [
                    {
                        "id": id
                    } for id in company_ids
                    ]
                }) if company_ids else None

            formatted_contacts = []
            if contacts_batch and contacts_batch.results:
                for contact in contacts_batch.results:
                    contact_dict = contact.to_dict()
                    formatted_contacts.append({
                        "contact_id": int(contact_dict['id']),
                        "contact_email_addresses": [
                        contact_dict['properties'].get('email')
                        ] if contact_dict['properties'].get('email') else [],
                        "contact_name": f"{contact_dict['properties'].get('firstname', '')} {contact_dict['properties'].get('lastname', '')}".strip()
                    })

            formatted_companies = []
            if companies_batch and companies_batch.results:
                for company in companies_batch.results:
                    company_dict = company.to_dict()
                    primary_domain = company_dict['properties'].get('domain')
                    additional_domains = company_dict['properties'].get(
                        'hs_additional_domains',
                        '').split(';') if company_dict['properties'].get(
                            'hs_additional_domains') else []
                    website = company_dict['properties'].get('website')
                    all_domains = list(
                        set(filter(None, [primary_domain, website] + additional_domains)))

                    formatted_companies.append({
                        "company_id": int(company_dict['id']),
                        "company_name": company_dict['properties'].get('name', ''),
                        "company_domains": all_domains
                    })

            return {
                **deal_dict,
                "owner_email": owner_email,
                "associatedContacts": formatted_contacts,
                "associatedCompanies": formatted_companies
            }

        except ApiException as e:
            print(f"Exception when processing deal {deal.id}: {e}\n")
            return deal_dict

    def fetch_deals_with_associations(hubspot_client):
        try:
            # Fetch 25 deals
            deals_page = hubspot_client.crm.deals.basic_api.get_page(limit=25)
            deals = deals_page.results

            # Process each deal
            deals_with_associations = [Functions.process_deal(deal) for deal in deals]

            print("Deals with associations have been fetched successfully")
            print(simplejson.dumps(deals_with_associations, indent=2, ignore_nan=True, default=str))
            return deals_with_associations

        except ApiException as e:
            print(f"Exception when fetching deals: {e}\n")
            return f"Error: {e}\n"