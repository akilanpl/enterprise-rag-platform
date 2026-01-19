from fastapi import Header, HTTPException

def authenticate(api_key: str = Header(...)):
    if api_key not in {"ENTERPRISE_KEY_1"}:
        raise HTTPException(status_code=401, detail="Unauthorized")
