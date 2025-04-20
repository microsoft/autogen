import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger
from sqlalchemy import exc, inspect, text
from sqlmodel import Session, SQLModel, and_, create_engine, select

from ..datamodel import BaseDBModel, Response, Team, Tool
from ..teammanager import TeamManager
from ..toolmanager import ToolManager
from .schema_manager import SchemaManager


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "get_secret_value") and callable(obj.get_secret_value):
            return obj.get_secret_value()
        return super().default(obj)


class DatabaseManager:
    _init_lock = threading.Lock()

    def __init__(self, engine_uri: str, base_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize DatabaseManager with database connection settings.
        Does not perform any database operations.

        Args:
            engine_uri: Database connection URI (e.g. sqlite:///db.sqlite3)
            base_dir: Base directory for migration files. If None, uses current directory
        """
        connection_args = {"check_same_thread": True} if "sqlite" in engine_uri else {}

        if base_dir is not None and isinstance(base_dir, str):
            base_dir = Path(base_dir)

        self.engine = create_engine(
            engine_uri, connect_args=connection_args, json_serializer=lambda obj: json.dumps(obj, cls=CustomJSONEncoder)
        )
        self.schema_manager = SchemaManager(
            engine=self.engine,
            base_dir=base_dir,
        )

    def _should_auto_upgrade(self) -> bool:
        """
        Check if auto upgrade should run based on schema differences
        """
        needs_upgrade, _ = self.schema_manager.check_schema_status()
        return needs_upgrade

    def initialize_database(self, auto_upgrade: bool = False, force_init_alembic: bool = True) -> Response:
        """
        Initialize database and migrations in the correct order.

        Args:
            auto_upgrade: If True, automatically generate and apply migrations for schema changes
            force_init_alembic: If True, reinitialize alembic configuration even if it exists
        """
        if not self._init_lock.acquire(blocking=False):
            return Response(message="Database initialization already in progress", status=False)

        try:
            # Enable foreign key constraints for SQLite
            if "sqlite" in str(self.engine.url):
                with self.engine.connect() as conn:
                    conn.execute(text("PRAGMA foreign_keys=ON"))
            inspector = inspect(self.engine)
            tables_exist = inspector.get_table_names()
            if not tables_exist:
                logger.info("Creating database tables...")
                SQLModel.metadata.create_all(self.engine)

                if self.schema_manager.initialize_migrations(force=force_init_alembic):
                    return Response(message="Database initialized successfully", status=True)
                return Response(message="Failed to initialize migrations", status=False)

            # Handle existing database
            if auto_upgrade or self._should_auto_upgrade():
                logger.info("Checking database schema...")
                if self.schema_manager.ensure_schema_up_to_date():
                    return Response(message="Database schema is up to date", status=True)
                return Response(message="Database upgrade failed", status=False)

            return Response(message="Database is ready", status=True)

        except Exception as e:
            error_msg = f"Database initialization failed: {str(e)}"
            logger.error(error_msg)
            return Response(message=error_msg, status=False)
        finally:
            self._init_lock.release()

    def reset_db(self, recreate_tables: bool = True) -> Response:
        """
        Reset the database by dropping all tables and optionally recreating them.

        Args:
            recreate_tables (bool): If True, recreates the tables after dropping them.
                                Set to False if you want to call create_db_and_tables() separately.
        """
        if not self._init_lock.acquire(blocking=False):
            logger.warning("Database reset already in progress")
            return Response(message="Database reset already in progress", status=False, data=None)

        try:
            # Dispose existing connections
            self.engine.dispose()
            with Session(self.engine) as session:
                try:
                    # Disable foreign key checks for SQLite
                    if "sqlite" in str(self.engine.url):
                        session.exec(text("PRAGMA foreign_keys=OFF"))  # type: ignore

                    # Drop all tables
                    SQLModel.metadata.drop_all(self.engine)
                    logger.info("All tables dropped successfully")

                    # Re-enable foreign key checks for SQLite
                    if "sqlite" in str(self.engine.url):
                        session.exec(text("PRAGMA foreign_keys=ON"))  # type: ignore

                    session.commit()

                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.close()
                    self._init_lock.release()

            if recreate_tables:
                logger.info("Recreating tables...")
                self.initialize_database(auto_upgrade=False, force_init_alembic=True)

            return Response(
                message="Database reset successfully" if recreate_tables else "Database tables dropped successfully",
                status=True,
                data=None,
            )

        except Exception as e:
            error_msg = f"Error while resetting database: {str(e)}"
            logger.error(error_msg)
            return Response(message=error_msg, status=False, data=None)
        finally:
            if self._init_lock.locked():
                self._init_lock.release()
                logger.info("Database reset lock released")

    def upsert(self, model: BaseDBModel, return_json: bool = True) -> Response:
        """Create or update an entity

        Args:
            model (SQLModel): The model instance to create or update
            return_json (bool, optional): If True, returns the model as a dictionary.
                If False, returns the SQLModel instance. Defaults to True.

        Returns:
            Response: Contains status, message and data (either dict or SQLModel based on return_json)
        """
        status = True
        model_class = type(model)
        existing_model = None

        with Session(self.engine) as session:
            try:
                existing_model = session.exec(select(model_class).where(model_class.id == model.id)).first()
                if existing_model:
                    model.updated_at = datetime.now()
                    for key, value in model.model_dump().items():
                        setattr(existing_model, key, value)
                    model = existing_model
                    session.add(model)
                else:
                    session.add(model)
                session.commit()
                session.refresh(model)
            except Exception as e:
                session.rollback()
                logger.error("Error while updating/creating " + str(model_class.__name__) + ": " + str(e))
                status = False

        return Response(
            message=(
                f"{model_class.__name__} Updated Successfully"
                if existing_model
                else f"{model_class.__name__} Created Successfully"
            ),
            status=status,
            data=model.model_dump() if return_json else model,
        )

    def _model_to_dict(self, model_obj):
        return {col.name: getattr(model_obj, col.name) for col in model_obj.__table__.columns}

    def get(
        self,
        model_class: type[BaseDBModel],
        filters: dict | None = None,
        return_json: bool = False,
        order: str = "desc",
    ):
        """List entities"""
        with Session(self.engine) as session:
            result = []
            status = True
            status_message = ""

            try:
                statement = select(model_class)  # type: ignore
                if filters:
                    conditions = [getattr(model_class, col) == value for col, value in filters.items()]
                    statement = statement.where(and_(*conditions))

                if hasattr(model_class, "created_at") and order:
                    order_by_clause = getattr(model_class.created_at, order)()  # Dynamically apply asc/desc
                    statement = statement.order_by(order_by_clause)

                items = session.exec(statement).all()
                result = [self._model_to_dict(item) if return_json else item for item in items]
                status_message = f"{model_class.__name__} Retrieved Successfully"
            except Exception as e:
                session.rollback()
                status = False
                status_message = f"Error while fetching {model_class.__name__}"
                logger.error("Error while getting items: " + str(model_class.__name__) + " " + str(e))

            return Response(message=status_message, status=status, data=result)

    def delete(self, model_class: type[BaseDBModel], filters: dict | None = None) -> Response:
        """Delete an entity"""
        status_message = ""
        status = True

        with Session(self.engine) as session:
            try:
                if "sqlite" in str(self.engine.url):
                    session.exec(text("PRAGMA foreign_keys=ON"))  # type: ignore
                statement = select(model_class)  # type: ignore
                if filters:
                    conditions = [getattr(model_class, col) == value for col, value in filters.items()]
                    statement = statement.where(and_(*conditions))

                rows = session.exec(statement).all()

                if rows:
                    for row in rows:
                        session.delete(row)
                    session.commit()
                    status_message = f"{model_class.__name__} Deleted Successfully"
                else:
                    status_message = "Row not found"
                    logger.info(f"Row with filters {filters} not found")

            except exc.IntegrityError as e:
                session.rollback()
                status = False
                status_message = f"Integrity error: The {model_class.__name__} is linked to another entity and cannot be deleted. {e}"
                # Log the specific integrity error
                logger.error(status_message)
            except Exception as e:
                session.rollback()
                status = False
                status_message = f"Error while deleting: {e}"
                logger.error(status_message)

        return Response(message=status_message, status=status, data=None)

    async def import_tools_from_directory(self, dir: Union[str, Path], user_id: str) -> Response:
        DEFAULT_TOOL_FILE = "tools.json"
        tool_file = Path(dir) / DEFAULT_TOOL_FILE

        # Just return if the file doesn't exist
        if not tool_file.exists():
            return Response(message="Tools file not found. Skipping import.", status=True)

        try:
            config = await ToolManager.load_from_file(tool_file)

            for cfg in config:
                exists = await self._check_tool_exists(cfg, user_id)
                if exists:
                    logger.debug(f"Tool already exists: {cfg.get('label')}. Skipping")
                    continue

                try:
                    tool_db = Tool(user_id=user_id, component=cfg)
                    self.upsert(tool_db)
                    logger.debug(f"Tool imported: {cfg.get('label')}")
                except Exception as e:
                    logger.error(f"Failed to import tool: {str(e)}")
                    return Response(message=str(e), status=False)
            return Response(message="Tools imported successfully", status=True)

        except Exception as e:
            logger.error(f"Failed to import tools: {str(e)}")
            return Response(message=str(e), status=False)

    async def import_team(
        self, team_config: Union[str, Path, dict], user_id: str, check_exists: bool = False
    ) -> Response:
        try:
            # Load config if path provided -- but ignore the tools.json file.
            if isinstance(team_config, (str, Path)):
                config = await TeamManager.load_from_file(team_config)
            else:
                config = team_config

            # Check existence if requested
            if check_exists:
                existing = await self._check_team_exists(config, user_id)
                if existing:
                    return Response(
                        message="Identical team configuration already exists", status=True, data={"id": existing.id}
                    )

            # Store in database
            team_db = Team(user_id=user_id, component=config)

            result = self.upsert(team_db)
            return result

        except Exception as e:
            logger.error(f"Failed to import team: {str(e)}")
            return Response(message=str(e), status=False)

    async def import_teams_from_directory(
        self, directory: Union[str, Path], user_id: str, check_exists: bool = False
    ) -> Response:
        """
        Import all team configurations from a directory.

        Args:
            directory: Path to directory containing team configs
            user_id: User ID to associate with imported teams
            check_exists: Whether to check for existing teams

        Returns:
            Response containing import results for all files
        """
        try:
            # Load all configs from directory
            configs = await TeamManager.load_from_directory(directory)

            results = []
            for config in configs:
                try:
                    result = await self.import_team(team_config=config, user_id=user_id, check_exists=check_exists)

                    # Add result info
                    results.append(
                        {
                            "status": result.status,
                            "message": result.message,
                            "id": result.data.get("id") if result.data and result.data is not None else None,
                        }
                    )

                except Exception as e:
                    logger.error(f"Failed to import team config: {str(e)}")
                    results.append({"status": False, "message": str(e), "id": None})

            return Response(message="Directory import complete", status=True, data=results)

        except Exception as e:
            logger.error(f"Failed to import directory: {str(e)}")
            return Response(message=str(e), status=False)

    async def _check_tool_exists(self, config: dict, user_id: str) -> Optional[Tool]:
        """Check if identical tool config already exists"""
        tools = self.get(Tool, {"user_id": user_id}).data

        for tool in tools:
            if tool.component == config:
                return tool

        return None

    async def _check_team_exists(self, config: dict, user_id: str) -> Optional[Team]:
        """Check if identical team config already exists"""
        response = self.get(Team, {"user_id": user_id})
        teams = response.data if response.status and response.data is not None else []

        for team in teams:
            if team.component == config:
                return team

        return None

    async def close(self):
        """Close database connections and cleanup resources"""
        logger.info("Closing database connections...")
        try:
            # Dispose of the SQLAlchemy engine
            self.engine.dispose()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")
            raise
