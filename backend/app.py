from fastapi import FastAPI
from backend.api import api_router
from backend.api.health import router as health_router
from backend.api.evaluate import router as evaluate_router
from backend.api.rules import router as rules_router
from backend.api.variables import router as variables_router
from backend.api.import_export import router as import_export_router
from backend.api.analytics import router as analytics_router
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.rules_engine.persistence import create_all_tables
from backend.rules_engine.registry import seed_variables_from_json
from backend.rules_engine.registry import infer_variables_from_csvs
from backend.rules_engine.persistence import get_session, Variable
from sqlalchemy import select
from backend.rules_engine.persistence import seed_rules_from_json


def create_app() -> FastAPI:
    app = FastAPI(title="ETERNA DX Rules Engine", version="0.1.0")

    # CORS (dev): permitir UI local
    # CORS (dev): permitir UI local. En desarrollo abrimos a '*'
    # CORS abierto (desarrollo). Si quieres restringir, ajusta aquí.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(evaluate_router)
    app.include_router(rules_router)
    app.include_router(variables_router)
    app.include_router(import_export_router)
    app.include_router(analytics_router)

    @app.on_event("startup")
    def on_startup() -> None:
        # DB tables
        create_all_tables()
        # Seeds (idempotentes)
        seed_variables_from_json("backend/seeds/variables_seed.json")
        seed_rules_from_json("backend/seeds/rules_seed.json")
        # Inferencia básica desde CSV reales (idempotente)
        try:
            inferred = infer_variables_from_csvs()
            if inferred:
                with get_session() as session:
                    for item in inferred:
                        exists = session.scalar(select(Variable).where(Variable.key == item.get("key")))
                        if exists:
                            continue
                        session.add(
                            Variable(
                                key=item.get("key"),
                                label=None,
                                description=None,
                                unit=None,
                                type=item.get("type", "number"),
                                allowed_aggregators=item.get("allowed_aggregators", {}),
                                valid_min=None,
                                valid_max=None,
                                missing_policy="skip",
                                decimals=None,
                                category=None,
                                tenant_id=item.get("tenant_id", "default"),
                                examples=None,
                            )
                        )
                    session.commit()
        except Exception:
            # No bloquear el arranque si hay problemas con CSV
            pass

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host=settings.app_host, port=settings.app_port, reload=True)


