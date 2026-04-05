import json
from services.sticker_service import StickerService

def test_sticker_service_empty_catalog(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"greeting": []}))
    service = StickerService(str(catalog), str(tmp_path))
    assert service.get_sticker_for_event("greeting") is None

def test_sticker_service_returns_sticker(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"praise": ["sticker_id_1"]}))
    service = StickerService(str(catalog), str(tmp_path))
    assert service.get_sticker_for_event("praise") == "sticker_id_1"
