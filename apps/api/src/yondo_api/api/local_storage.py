from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from yondo_api.api.errors import ApplicationError
from yondo_api.integrations.local_storage import LocalObjectStorage

router = APIRouter(prefix='/storage/local', tags=['development storage'], include_in_schema=False)


@router.get('/{key:path}')
async def download(key: str, expires: int, signature: str, request: Request):
    storage = request.app.state.object_storage
    if not isinstance(storage, LocalObjectStorage) or not storage.verify(key, expires, signature):
        raise ApplicationError('not_found', 'Not found', 404)
    try:
        path = storage.path_for(key)
    except ValueError as exc:
        raise ApplicationError('not_found', 'Not found', 404) from exc
    if not path.is_file():
        raise ApplicationError('not_found', 'Not found', 404)
    return FileResponse(path, media_type='image/jpeg')
