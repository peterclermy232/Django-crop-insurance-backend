from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """`?page=2&page_size=10`; without `page_size` pages hold PAGE_SIZE records as before."""
    page_size_query_param = 'page_size'
    max_page_size = 100
