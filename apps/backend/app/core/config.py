from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "v4nex-backend"
    internal_api_prefix: str = "/_v4nex"
    public_domain: str = "v4nex.com"


settings = Settings()
