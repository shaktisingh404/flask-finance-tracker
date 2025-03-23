# from flask import request, url_for
# from sqlalchemy.orm import Query


# class PaginatedResult:

#     def __init__(self, query, page=1, per_page=10, error_out=False):

#         self.query = query
#         self.page = page
#         self.per_page = per_page
#         self.error_out = error_out

#         # Get paginated items
#         self.pagination = query.paginate(
#             page=page, per_page=per_page, error_out=error_out
#         )

#     @property
#     def items(self):
#         """Get current page items"""
#         return self.pagination.items

#     @property
#     def total(self):
#         """Get total number of items"""
#         return self.pagination.total

#     def to_dict(self, schema, endpoint=None, **kwargs):

#         serialized_items = schema.dump(self.items)

#         # Build response with count and items
#         result = {"count": self.pagination.total, "items": serialized_items}

#         # Add navigation links if endpoint is provided
#         if endpoint:
#             # Add parameters that should be included in all links
#             params = kwargs.copy()
#             params["per_page"] = self.per_page

#             # Next page link
#             if self.pagination.has_next:
#                 params["page"] = self.page + 1
#                 result["next"] = url_for(endpoint, **params, _external=True)

#             # Previous page link
#             if self.pagination.has_prev:
#                 params["page"] = self.page - 1
#                 result["previous"] = url_for(endpoint, **params, _external=True)

#         return result

#     def _get_pagination_links(self, endpoint, **kwargs):

#         links = {}

#         # Add parameters that should be included in all links
#         params = kwargs.copy()
#         params["per_page"] = self.per_page

#         # First page link
#         params["page"] = 1
#         links["first"] = url_for(endpoint, **params, _external=True)

#         # Last page link
#         params["page"] = self.pagination.pages
#         links["last"] = url_for(endpoint, **params, _external=True)

#         # Previous page link
#         if self.pagination.has_prev:
#             params["page"] = self.page - 1
#             links["prev"] = url_for(endpoint, **params, _external=True)

#         # Next page link
#         if self.pagination.has_next:
#             params["page"] = self.page + 1
#             links["next"] = url_for(endpoint, **params, _external=True)

#         return links


# def paginate(query, schema, endpoint=None, **kwargs):

#     # Get pagination parameters from request or use defaults
#     page = kwargs.pop("page", request.args.get("page", 1, type=int))
#     per_page = kwargs.pop("per_page", request.args.get("per_page", 10, type=int))

#     # Ensure reasonable limits for pagination
#     per_page = min(max(per_page, 1), 100)  # Between 1 and 100

#     # Create paginated result
#     paginated_result = PaginatedResult(query, page, per_page)

#     # Return formatted result
#     return paginated_result.to_dict(schema, endpoint, **kwargs)
from flask import request, url_for
from sqlalchemy.orm import Query


class PaginatedResult:

    def __init__(self, query, page=1, per_page=10, error_out=False):
        self.query = query
        self.page = page
        self.per_page = per_page
        self.error_out = error_out

        # Get paginated items
        self.pagination = query.paginate(
            page=page, per_page=per_page, error_out=error_out
        )

    @property
    def items(self):
        """Get current page items"""
        return self.pagination.items

    @property
    def total(self):
        """Get total number of items"""
        return self.pagination.total

    def to_dict(self, schema, endpoint=None, **kwargs):
        serialized_items = schema.dump(self.items)

        # Build response with count and items
        result = {
            "count": self.pagination.total,
            "next": None,
            "previous": None,
            "items": serialized_items,
        }

        # Add navigation links if endpoint is provided
        if endpoint:
            # Add parameters that should be included in all links
            params = kwargs.copy()
            params["per_page"] = self.per_page
            # Generate simple URLs if url_for fails
            base_url = request.base_url
            query_args = "&".join(
                [f"{k}={v}" for k, v in params.items() if k != "page"]
            )

            # Next page link
            if self.pagination.has_next:
                try:
                    params["page"] = self.page + 1
                    result["next"] = url_for(endpoint, **params, _external=True)
                except Exception:
                    # Fallback to a basic URL format
                    next_page = self.page + 1
                    result["next"] = f"{base_url}?page={next_page}&{query_args}"

            # Previous page link
            if self.pagination.has_prev:
                try:
                    params["page"] = self.page - 1
                    result["previous"] = url_for(endpoint, **params, _external=True)
                except Exception:
                    # Fallback to a basic URL format
                    prev_page = self.page - 1
                    result["previous"] = f"{base_url}?page={prev_page}&{query_args}"

        return result


def paginate(query, schema, endpoint=None, **kwargs):
    # Get pagination parameters from request or use defaults
    page = kwargs.pop("page", request.args.get("page", 1, type=int))
    per_page = kwargs.pop("per_page", request.args.get("per_page", 10, type=int))

    # Ensure reasonable limits for pagination
    per_page = min(max(per_page, 1), 100)  # Between 1 and 100

    # Create paginated result
    paginated_result = PaginatedResult(query, page, per_page)

    # Return formatted result
    return paginated_result.to_dict(schema, endpoint, **kwargs)
