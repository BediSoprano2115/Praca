from flask import request,jsonify
from functools import wraps

import os

class Decorators:
    """
    Main routes decorators

    This functions will limit the routes access or other requirements
    """
    def require_api_key(hs):
        def decorator (f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                api_key = request.headers.get('Authorization')
                if api_key and api_key == hs:
                    return f(*args, **kwargs)
                else:
                    return jsonify({"error": "Unauthorized"}), 401
            return decorated_function
        return decorator