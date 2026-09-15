from rest_framework.response import Response
from core.models import Client

def resolve_client(request):
    """
    Returns the Client for request.user, raising/returning None if absent.
    """
    if not request.user or not request.user.is_authenticated:
        return None
    try:
        return Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return None

def require_self_or_provider(request, client_id):
    """
    Returns (client, error_response). Allows access if the caller IS that client, OR the caller is a PROVIDER and target.referred_by_id == caller.id, OR the caller is staff/superuser. Otherwise returns a 404 (not 403, to avoid enumeration).
    """
    if not request.user or not request.user.is_authenticated:
        return None, Response({"error": "Not found"}, status=404)

    caller = resolve_client(request)
    
    try:
        target = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return None, Response({"error": "Not found"}, status=404)
        
    if request.user.is_staff or request.user.is_superuser:
        return target, None

    if caller and caller.id == target.id:
        return target, None
        
    if caller and caller.type == "PROVIDER" and target.referred_by_id == caller.id:
        return target, None
        
    return None, Response({"error": "Not found"}, status=404)
