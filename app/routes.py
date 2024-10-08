from app import app
from flask import render_template, jsonify, request
import requests
from app.functions import Functions
from app.decorators import Decorators
from config import Config
from datetime import datetime
import re

@app.route("/")
@app.route("/index")
def index():
    """ 
    Main page --> Landing page
    """
    return render_template("index.html")

@app.route('/get-deals-with-associations', methods=['GET'])
@Decorators.require_api_key(hs=Config.hs)
def get_deals():
    deals = Functions.fetch_deals_with_associations()
    return jsonify(deals)

@app.route('/blog')
def blog():
    """
    Blog with posts imported from HubSpot, paginated, filtered by category, and searchable by post name.
    Also, fetches the latest posts for display in the 'Latest HubSpot Posts' section.
    """
    url_posts = Config.HUBSPOT_POSTS_URL
    url_tags = Config.HUBSPOT_TAGS_URL
    token = Config.HUBSPOT_API_TOKEN

    headers = {
        'accept': "application/json",
        'authorization': f"Bearer {token}"
    }

    # Retrieve the page, category, and search query from the request
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '', type=str)
    search_query = request.args.get('search', '', type=str)

    # Fetch all posts without pagination
    params = {
        'limit': 100,  # Fetch a larger number to allow for filtering and getting the latest posts
        'orderBy': '-created'  # Fetch the posts ordered by creation date in descending order
    }

    response_posts = requests.get(url_posts, headers=headers, params=params)
    if response_posts.status_code != 200:
        return jsonify({"error": "Failed to fetch posts from HubSpot"}), 500

    blog_data = response_posts.json()
    blog = blog_data.get("results", [])

    # Fetch tags
    response_tags = requests.get(url_tags, headers=headers)
    if response_tags.status_code != 200:
        return jsonify({"error": "Failed to fetch tags from HubSpot"}), 500

    tags_data = response_tags.json()
    tags = tags_data.get("results", [])

    # Create a dictionary mapping tag IDs to their names
    tag_map = {str(tag['id']): tag['name'] for tag in tags}

    # Replace tag IDs with names in the posts
    for post in blog:
        post['category_names'] = [tag_map.get(str(tag_id), 'Unknown Tag') for tag_id in post.get('tagIds', [])]

    # Initialize category_id to None
    category_id = None

    if category:
        # Find the tag ID for the given category name
        category_id = next((tag_id for tag_id, tag_name in tag_map.items() if tag_name == category), None)
        if category_id:
            blog = [post for post in blog if category_id in post.get('topic_ids', [])]

    # Apply search filtering
    if search_query:
        blog = [post for post in blog if search_query.lower() in post['name'].lower()]

    # Pagination logic
    posts_per_page = 15
    total_results = len(blog)
    has_next = (page * posts_per_page) < total_results

    # Calculate pagination
    start = (page - 1) * posts_per_page
    end = start + posts_per_page
    blog = blog[start:end]  # Get only the posts for the current page

    # Fetch the 4 latest posts
    latest_posts = blog_data.get("results", [])[:4]

    def format_post_date(created_date_str):
        """Function to format post date from ISO to a readable format."""
        if created_date_str:
            return datetime.fromisoformat(created_date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        return "Date not available"

    # Format the publish dates for the blog posts
    for post in blog:
        post['formatted_publish_date'] = format_post_date(post.get('created', ''))

    # Pass the blog posts, latest posts, and other variables to the template
    return render_template(
        "blog.html",
        blog=blog,
        page=page,
        has_next=has_next,
        tags=tags,
        selected_category=category,
        search_query=search_query,
        latest_posts=latest_posts
    )



@app.route("/request-services")
def request_services():
    """
    Request services page
    """
    return render_template("request-services.html")


@app.route("/shop")
@app.route("/products")
def products():
    """
    Products or Shop page
    """
    products = [
        {"name": "Product1", "description": "Description1"},
        {"name": "Product2", "description": "Description2"},
        {"name": "Product3", "description": "Description3"}
    ]
    return render_template("products.html", products=products)


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def single_post(post_id):
    token = Config.HUBSPOT_API_TOKEN
    base_url = Config.HUBSPOT_POSTS_URL

    headers = {
        'accept': "application/json",
        'authorization': f"Bearer {token}"
    }

    # Fetch all tags to create the tag_map
    url_tags = Config.HUBSPOT_TAGS_URL
    response_tags = requests.get(url_tags, headers=headers)
    if response_tags.status_code != 200:
        return jsonify({"error": "Failed to fetch tags from HubSpot"}), 500

    tags_data = response_tags.json()
    tags = tags_data.get("results", [])
    
    # Create a mapping of tag IDs to their names
    tag_map = {str(tag['id']): tag['name'] for tag in tags}

    # Fetch the main post by post_id
    url_post = f"{base_url}/{post_id}"
    response_post = requests.get(url_post, headers=headers)
    if response_post.status_code != 200:
        return jsonify({"error": "Failed to fetch post from HubSpot"}), 500

    post_data = response_post.json()

    # Clean the entire post data
    cleaned_post_data = clean_post_data(post_data)

    # Replace tag IDs with names in the cleaned post data
    cleaned_post_data['category_names'] = [
        tag_map.get(str(tag_id), 'Unknown Tag') for tag_id in cleaned_post_data.get('tagIds', [])
    ]

    # Fetch the 4 latest posts (optional)
    latest_posts_data = fetch_latest_posts(base_url, headers)

    # Format the created date
    created_date_str = cleaned_post_data.get('created', '')
    formatted_created_date = format_post_date(created_date_str)

    # Prepare the data for rendering
    context = {
        'data': cleaned_post_data,
        'latest_posts': latest_posts_data,
        'created_date': formatted_created_date,
        'tags': cleaned_post_data['category_names']  # Pass category names to the template
    }

    # Render the template with the data
    return render_template('single_post.html', **context)


def clean_post_content(content):
    """Function to clean the post content by removing unwanted parts like placeholders and metadata."""
    content = re.sub(r'{%.*?%}', '', content)  # Removes template placeholders
    content = re.sub(r'{{.*?}}', '', content)  # Removes Mustache-style placeholders
    content = re.sub(r'<[^>]+>', '', content)  # Removes HTML tags
    content = re.sub(r"{'.*?'}", '', content)  # Removes content in single quotes
    content = re.sub(r'{\".*?\"}', '', content)  # Removes content in double quotes
    content = re.sub(r'\{.*?\}', '', content)   # Removes anything inside curly braces
    content = re.sub(r'widget-type-space[^"]*', '', content)
    content = re.sub(r'\d+"@hubspot/[^"]*"', '', content)

    unwanted_keys = ['slug', 'state', 'updatedById', 'useFeaturedImage']
    for key in unwanted_keys:
        content = re.sub(rf'"{key}":.*?,', '', content)  # Removes metadata keys

    content = re.sub(r'\\n', ' ', content)
    content = re.sub(r'\n', ' ', content)
    content = re.sub(r'\s+', ' ', content).strip()  # Normalize spaces
    content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL)  # Remove <script> tags

    return content


def clean_post_data(post_data):
    """Function to clean the post data dictionary by removing unwanted parts."""
    if 'postBody' in post_data:
        post_data['postBody'] = clean_post_content(post_data['postBody'])

    unwanted_keys = ['slug', 'state', 'updatedById', 'useFeaturedImage']
    for key in unwanted_keys:
        post_data.pop(key, None)

    return post_data


def fetch_hubdb_tables(table_ids, hubdb_url, headers):
    """Function to fetch HubDB table rows for given table IDs."""
    tables_data = {}
    for table_id in table_ids:
        url = f"{hubdb_url}/{table_id}/rows"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tables_data[table_id] = response.json()
        else:
            print(f"Error fetching HubDB table {table_id}. Status code: {response.status_code}")
    return tables_data


def fetch_latest_posts(base_url, headers, limit=4):
    """Fetch the latest blog posts (for example, the 4 latest posts)"""
    params = {'limit': limit, 'orderBy': '-created'}
    response_latest_posts = requests.get(base_url, headers=headers, params=params)
    if response_latest_posts.status_code == 200:
        return response_latest_posts.json().get('results', [])
    return []


def format_post_date(created_date_str):
    """Function to format post date from ISO to a readable format."""
    if created_date_str:
        return datetime.fromisoformat(created_date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    return "Date not available"