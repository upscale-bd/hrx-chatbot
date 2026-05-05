from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from common.logger import get_logger
from common.response import api_response
from config.config import init_settings
from infrastructure import database
from infrastructure.database import init_db
from services.auth.hrx_auth import HRXAuthService

# Import routers
from app.chatbot.handler.chat_handler import router as chat_router
from app.mcp.handler.tool_handler import router as tool_router
from app.report.handler.report_handler import router as report_router
from app.auth.handler.auth_handler import router as auth_router
from app.audio_comparison.handler.audio_comparison_handler import router as audio_comparison_router
from app.admin.handler.admin_script_handler import router as admin_script_router


logger = get_logger("serve")
security = HTTPBearer()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logger.info("[serve] Assembling FastAPI application...")
    app = FastAPI(
        title="HRX Chatbot API",
        description="AI-powered HRX chatbot for HR modules (attendance, leave, payroll)",
        version="1.0.0",
    )
    logger.info("[serve] FastAPI instance created")
    
    # Add CORS middleware to allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )
    logger.info("[serve] CORS middleware configured - allowing all origins")
    
    # Custom OpenAPI schema with Bearer token security
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="HRX Chatbot API",
            version="1.0.0",
            description="AI-powered HRX chatbot for HR modules",
            routes=app.routes,
        )
        
        # Add Bearer token security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "📝 Enter your Bearer token from external HRX service\n\nExample: eyJhbGciOiJIUzI1NiIs..."
            }
        }
        
        # Apply Bearer security to all endpoints
        for path in openapi_schema["paths"].values():
            for operation in path.values():
                if isinstance(operation, dict) and "responses" in operation:
                    operation["security"] = [{"Bearer": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    logger.info("[serve] Swagger UI with Bearer token security configured")

    @app.on_event("startup")
    async def on_startup():
        logger.info("[serve] ── startup: initializing settings...")
        init_settings()
        logger.info("[serve] ── startup: settings loaded")
        logger.info("[serve] ── startup: initializing database...")
        if init_db():
            logger.info("[serve] ── startup: database initialized successfully")
        else:
            logger.warning("[serve] ── startup: database initialization failed — check DB connection")
        logger.info("[serve] ── startup: seeding MCP tool registry...")
        try:
            from app.mcp.seed.tool_seed import seed_tools
            db = database.SessionLocal()
            seed_tools(db)
            db.close()
            logger.info("[serve] ── startup: tool registry seed complete")
        except Exception as exc:
            logger.error(f"[serve] ── startup: tool seed failed — {exc}")
        logger.info("[serve] ── startup: complete")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            f"[serve] Validation error on {request.method} {request.url.path}: {exc.errors()}"
        )
        errors = [
            {
                "field": ".".join(map(str, err["loc"])),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        logger.warning(f"[serve] Returning 422 with {len(errors)} validation error(s)")
        return api_response(
            status_code=422,
            message="Validation Error",
            error={"type": "ValidationError", "details": errors},
        )

    # Middleware: Auto-cache Bearer token from Swagger Authorization
    @app.middleware("http")
    async def auto_cache_bearer_token(request: Request, call_next):
        """Extract Bearer token from Authorization header and cache it."""
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header.replace("Bearer ", "").strip()
            if bearer_token:
                # Auto-cache the token for 24 hours
                HRXAuthService.set_token(bearer_token, ttl_hours=24)
                logger.info(f"[serve] 🔐 Bearer token detected in Authorization header | length={len(bearer_token)}")
        
        response = await call_next(request)
        return response
    
    logger.info("[serve] Registering chat router...")
    app.include_router(chat_router)
    logger.info("[serve] Registering MCP tool router...")
    app.include_router(tool_router)
    logger.info("[serve] Registering report download router...")
    app.include_router(report_router)
    logger.info("[serve] Registering authentication router...")
    app.include_router(auth_router)
    logger.info("[serve] Registering audio comparison router...")
    app.include_router(audio_comparison_router)
    logger.info("[serve] Registering admin script router...")
    app.include_router(admin_script_router)
    logger.info("[serve] All routers registered ✅")

    @app.get("/health")
    async def health_check():
        logger.info("[serve] Health check requested")
        return {"status": "healthy", "service": "hrx-chatbot"}

    return app


logger.info("[serve] Building application instance...")
app = create_app()
logger.info("[serve] Application instance ready")