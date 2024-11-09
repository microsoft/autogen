import threading
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import exc, text, func
from sqlmodel import Session, SQLModel, and_, create_engine, select
from .schema_manager import SchemaManager

from ..datamodel import (
    Response,
    LinkTypes
)
# from .dbutils import init_db_samples


class DatabaseManager:
    """A class to manage database operations"""

    _init_lock = threading.Lock()

    def __init__(self, engine_uri: str, auto_upgrade: bool = True):
        connection_args = {
            "check_same_thread": True} if "sqlite" in engine_uri else {}
        self.engine = create_engine(engine_uri, connect_args=connection_args)
        self.schema_manager = SchemaManager(
            engine=self.engine,
            auto_upgrade=auto_upgrade,
        )

        # Check and upgrade on startup
        upgraded, status = self.schema_manager.check_and_upgrade()
        if upgraded:
            logger.info("Database schema was upgraded automatically")
        else:
            logger.info(f"Schema status: {status}")

    def reset_db(self, recreate_tables: bool = True):
        """
        Reset the database by dropping all tables and optionally recreating them.

        Args:
            recreate_tables (bool): If True, recreates the tables after dropping them.
                                Set to False if you want to call create_db_and_tables() separately.
        """
        if not self._init_lock.acquire(blocking=False):
            logger.warning("Database reset already in progress")
            return Response(
                message="Database reset already in progress",
                status=False,
                data=None
            )

        try:
            # Dispose existing connections
            self.engine.dispose()
            with Session(self.engine) as session:
                try:
                    # Disable foreign key checks for SQLite
                    if 'sqlite' in str(self.engine.url):
                        session.exec(text('PRAGMA foreign_keys=OFF'))

                    # Drop all tables
                    SQLModel.metadata.drop_all(self.engine)
                    logger.info("All tables dropped successfully")

                    # Re-enable foreign key checks for SQLite
                    if 'sqlite' in str(self.engine.url):
                        session.exec(text('PRAGMA foreign_keys=ON'))

                    session.commit()

                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.close()
                    self._init_lock.release()

            if recreate_tables:
                logger.info("Recreating tables...")
                self.create_db_and_tables()

            return Response(
                message="Database reset successfully" if recreate_tables else "Database tables dropped successfully",
                status=True,
                data=None
            )

        except Exception as e:
            error_msg = f"Error while resetting database: {str(e)}"
            logger.error(error_msg)
            return Response(
                message=error_msg,
                status=False,
                data=None
            )
        finally:
            if self._init_lock.locked():
                self._init_lock.release()
                logger.info("Database reset lock released")

    def create_db_and_tables(self):
        """Create a new database and tables"""
        with self._init_lock:
            try:
                SQLModel.metadata.create_all(self.engine)
                logger.info("Database tables created successfully")
                try:
                    # init_db_samples(self)
                    pass
                except Exception as e:
                    logger.info(
                        "Error while initializing database samples: " + str(e))
            except Exception as e:
                logger.info("Error while creating database tables:" + str(e))

    def upsert(self, model: SQLModel, return_json: bool = True):
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
                existing_model = session.exec(
                    select(model_class).where(model_class.id == model.id)).first()
                if existing_model:
                    model.updated_at = datetime.now()
                    for key, value in model.model_dump().items():
                        setattr(existing_model, key, value)
                    model = existing_model  # Use the updated existing model
                    session.add(model)
                else:
                    session.add(model)
                session.commit()
                session.refresh(model)
            except Exception as e:
                session.rollback()
                logger.error("Error while updating/creating " +
                             str(model_class.__name__) + ": " + str(e))
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
        model_class: SQLModel,
        filters: dict = None,
        return_json: bool = False,
        order: str = "desc",
    ):
        """List entities"""
        with Session(self.engine) as session:
            result = []
            status = True
            status_message = ""

            try:
                statement = select(model_class)
                if filters:
                    conditions = [getattr(model_class, col) ==
                                  value for col, value in filters.items()]
                    statement = statement.where(and_(*conditions))

                if hasattr(model_class, "created_at") and order:
                    order_by_clause = getattr(
                        model_class.created_at, order)()  # Dynamically apply asc/desc
                    statement = statement.order_by(order_by_clause)

                items = session.exec(statement).all()
                result = [self._model_to_dict(
                    item) if return_json else item for item in items]
                status_message = f"{model_class.__name__} Retrieved Successfully"
            except Exception as e:
                session.rollback()
                status = False
                status_message = f"Error while fetching {model_class.__name__}"
                logger.error("Error while getting items: " +
                             str(model_class.__name__) + " " + str(e))

            return Response(message=status_message, status=status, data=result)

    def delete(self, model_class: SQLModel, filters: dict = None):
        """Delete an entity"""
        status_message = ""
        status = True

        with Session(self.engine) as session:
            try:
                statement = select(model_class)
                if filters:
                    conditions = [
                        getattr(model_class, col) == value for col, value in filters.items()]
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

    def link(
        self,
        link_type: LinkTypes,
        primary_id: int,
        secondary_id: int,
        sequence: Optional[int] = None,
    ):
        """Link two entities with automatic sequence handling."""
        with Session(self.engine) as session:
            try:
                # Get classes from LinkTypes
                primary_class = link_type.primary_class
                secondary_class = link_type.secondary_class
                link_table = link_type.link_table

                # Get entities
                primary_entity = session.get(primary_class, primary_id)
                secondary_entity = session.get(secondary_class, secondary_id)

                if not primary_entity or not secondary_entity:
                    return Response(message="One or both entities do not exist", status=False)

                # Get field names
                primary_id_field = f"{primary_class.__name__.lower()}_id"
                secondary_id_field = f"{secondary_class.__name__.lower()}_id"

                # Check for existing link
                existing_link = session.exec(
                    select(link_table).where(
                        and_(
                            getattr(link_table, primary_id_field) == primary_id,
                            getattr(
                                link_table, secondary_id_field) == secondary_id
                        )
                    )
                ).first()

                if existing_link:
                    return Response(message="Link already exists", status=False)

                # Get the next sequence number if not provided
                if sequence is None:
                    max_seq_result = session.exec(
                        select(func.max(link_table.sequence)).where(
                            getattr(link_table, primary_id_field) == primary_id
                        )
                    ).first()
                    sequence = 0 if max_seq_result is None else max_seq_result + 1

                # Create new link
                new_link = link_table(**{
                    primary_id_field: primary_id,
                    secondary_id_field: secondary_id,
                    'sequence': sequence
                })
                session.add(new_link)
                session.commit()

                return Response(
                    message=f"Entities linked successfully with sequence {sequence}",
                    status=True
                )

            except Exception as e:
                session.rollback()
                return Response(message=f"Error linking entities: {str(e)}", status=False)

    def unlink(
        self,
        link_type: LinkTypes,
        primary_id: int,
        secondary_id: int,
        sequence: Optional[int] = None
    ):
        """Unlink two entities and reorder sequences if needed."""
        with Session(self.engine) as session:
            try:
                # Get classes from LinkTypes
                primary_class = link_type.primary_class
                secondary_class = link_type.secondary_class
                link_table = link_type.link_table

                # Get field names
                primary_id_field = f"{primary_class.__name__.lower()}_id"
                secondary_id_field = f"{secondary_class.__name__.lower()}_id"

                # Find existing link
                statement = select(link_table).where(
                    and_(
                        getattr(link_table, primary_id_field) == primary_id,
                        getattr(link_table, secondary_id_field) == secondary_id
                    )
                )

                if sequence is not None:
                    statement = statement.where(
                        link_table.sequence == sequence)

                existing_link = session.exec(statement).first()

                if not existing_link:
                    return Response(message="Link does not exist", status=False)

                deleted_sequence = existing_link.sequence
                session.delete(existing_link)

                # Reorder sequences for remaining links
                remaining_links = session.exec(
                    select(link_table)
                    .where(getattr(link_table, primary_id_field) == primary_id)
                    .where(link_table.sequence > deleted_sequence)
                    .order_by(link_table.sequence)
                ).all()

                # Decrease sequence numbers to fill the gap
                for link in remaining_links:
                    link.sequence -= 1

                session.commit()

                return Response(
                    message="Entities unlinked successfully and sequences reordered",
                    status=True
                )

            except Exception as e:
                session.rollback()
                return Response(message=f"Error unlinking entities: {str(e)}", status=False)

    def get_linked_entities(
        self,
        link_type: LinkTypes,
        primary_id: int,
        return_json: bool = False,
    ):
        """Get linked entities based on link type and primary ID, ordered by sequence."""
        with Session(self.engine) as session:
            try:
                # Get classes from LinkTypes
                primary_class = link_type.primary_class
                secondary_class = link_type.secondary_class
                link_table = link_type.link_table

                # Get field names
                primary_id_field = f"{primary_class.__name__.lower()}_id"
                secondary_id_field = f"{secondary_class.__name__.lower()}_id"

                # Query both link and entity, ordered by sequence
                items = session.exec(
                    select(secondary_class)
                    .join(link_table, getattr(link_table, secondary_id_field) == secondary_class.id)
                    .where(getattr(link_table, primary_id_field) == primary_id)
                    .order_by(link_table.sequence)
                ).all()

                result = [
                    item.model_dump() if return_json else item for item in items]

                return Response(
                    message="Linked entities retrieved successfully",
                    status=True,
                    data=result
                )

            except Exception as e:
                logger.error(f"Error getting linked entities: {str(e)}")
                return Response(
                    message=f"Error getting linked entities: {str(e)}",
                    status=False,
                    data=[]
                )
    # Add new close method

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
