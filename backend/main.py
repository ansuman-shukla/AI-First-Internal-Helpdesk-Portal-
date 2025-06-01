from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, home, tickets, webhooks, ai_bot, ai_agent, ws_chat, admin, notifications
from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.ai.startup import initialize_ai_services, get_ai_services_status, health_check as ai_health_check
from app.services.scheduler_service import scheduler_service
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("Starting application initialization")

    # Initialize MongoDB connection
    try:
        await connect_to_mongo()
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB: {e}")
        print(f"Warning: Could not connect to MongoDB: {e}")

    # Initialize AI services
    try:
        logger.info("Initializing AI services")
        ai_init_result = initialize_ai_services()

        if ai_init_result["success"]:
            logger.info("AI services initialized successfully")
        else:
            logger.warning(f"AI services initialization issues: {ai_init_result['errors']}")

        if ai_init_result["warnings"]:
            logger.warning(f"AI services warnings: {ai_init_result['warnings']}")

    except Exception as e:
        logger.error(f"Failed to initialize AI services: {e}")
        print(f"Warning: Could not initialize AI services: {e}")

    # Initialize scheduler
    try:
        logger.info("Starting scheduler service")
        await scheduler_service.start_scheduler()
        logger.info("Scheduler service started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler service: {e}")
        print(f"Warning: Could not start scheduler service: {e}")

    logger.info("Application startup complete")
    yield

    # Shutdown
    logger.info("Starting application shutdown")

    # Stop scheduler
    try:
        logger.info("Stopping scheduler service")
        await scheduler_service.stop_scheduler()
        logger.info("Scheduler service stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler service: {e}")

    await close_mongo_connection()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="AI-First Internal Helpdesk Portal",
    description="Internal ticket-based helpdesk system with AI routing, response suggestion, and misuse detection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(home.router)
app.include_router(tickets.router)
app.include_router(webhooks.router)
app.include_router(ai_bot.router)
app.include_router(ai_agent.router)
app.include_router(ws_chat.router)
app.include_router(admin.router)
app.include_router(notifications.router)

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"message": "AI-First Internal Helpdesk Portal API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "helpdesk-api"}

@app.get("/health/ai")
async def ai_health():
    """AI services health check endpoint"""
    try:
        health_status = ai_health_check()
        return {
            "service": "ai-services",
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "details": health_status
        }
    except Exception as e:
        return {
            "service": "ai-services",
            "status": "error",
            "error": str(e)
        }

@app.get("/status/ai")
async def ai_status():
    """AI services status endpoint"""
    try:
        status = get_ai_services_status()
        return {
            "service": "ai-services",
            "status": status
        }
    except Exception as e:
        return {
            "service": "ai-services",
            "error": str(e)
        }

@app.get("/health/scheduler")
async def scheduler_health():
    """Scheduler service health check endpoint"""
    try:
        status = scheduler_service.get_scheduler_status()
        return {
            "service": "scheduler",
            "status": "healthy" if status["running"] else "unhealthy",
            "details": status
        }
    except Exception as e:
        return {
            "service": "scheduler",
            "status": "error",
            "error": str(e)
        }
