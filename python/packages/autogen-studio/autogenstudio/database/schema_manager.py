import io
import os
import shutil
from contextlib import redirect_stdout
from pathlib import Path
from typing import List, Optional, Tuple

import sqlmodel
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from loguru import logger
from sqlalchemy import Engine, text
from sqlmodel import SQLModel


class SchemaManager:
    """
    Manages database schema validation and migrations using Alembic.
    Operations are initiated explicitly by DatabaseManager.
    """

    def __init__(
        self,
        engine: Engine,
        base_dir: Optional[Path] = None,
    ):
        """
        Initialize configuration only - no filesystem or DB operations.

        Args:
            engine: SQLAlchemy engine instance
            base_dir: Base directory for Alembic files. If None, uses current working directory
        """
        # Convert string path to Path object if necessary
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)

        self.engine = engine
        self.base_dir = base_dir or Path(__file__).parent
        self.alembic_dir = self.base_dir / "alembic"
        self.alembic_ini_path = self.base_dir / "alembic.ini"

    def initialize_migrations(self, force: bool = False) -> bool:
        try:
            if force:
                # logger.info("Force reinitialization of migrations...")
                self._cleanup_existing_alembic()
                if not self._initialize_alembic():
                    return False
            else:
                try:
                    self._validate_alembic_setup()
                    logger.info("Using existing Alembic configuration")
                    self._update_configuration()
                except FileNotFoundError:
                    logger.info("Initializing new Alembic configuration")
                    if not self._initialize_alembic():
                        return False

            # Only generate initial revision if alembic is properly initialized
            # logger.info("Creating initial migration...")
            return self.generate_revision("Initial schema") is not None

        except Exception as e:
            logger.error(f"Failed to initialize migrations: {e}")
            return False

    def _update_configuration(self) -> None:
        """Updates existing Alembic configuration with current settings."""
        logger.info("Updating existing Alembic configuration...")

        # Update alembic.ini
        config_content = self._generate_alembic_ini_content()
        with open(self.alembic_ini_path, "w") as f:
            f.write(config_content)

        # Update env.py
        env_path = self.alembic_dir / "env.py"
        if env_path.exists():
            self._update_env_py(env_path)
        else:
            self._create_minimal_env_py(env_path)

    def _cleanup_existing_alembic(self) -> None:
        """
        Completely remove existing Alembic configuration including versions.
        For fresh initialization, we don't need to preserve anything.
        """
        # logger.info("Cleaning up existing Alembic configuration...")

        # Remove entire alembic directory if it exists
        if self.alembic_dir.exists():
            import shutil

            shutil.rmtree(self.alembic_dir)
            logger.info(f"Removed alembic directory: {self.alembic_dir}")

        # Remove alembic.ini if it exists
        if self.alembic_ini_path.exists():
            self.alembic_ini_path.unlink()
            logger.info("Removed alembic.ini")

    def _ensure_alembic_setup(self, *, force: bool = False) -> None:
        """
        Ensures Alembic is properly set up, initializing if necessary.

        Args:
            force: If True, removes existing configuration and reinitializes
        """
        try:
            self._validate_alembic_setup()
            if force:
                logger.info("Force initialization requested. Cleaning up existing configuration...")
                self._cleanup_existing_alembic()
                self._initialize_alembic()
        except FileNotFoundError:
            logger.info("Alembic configuration not found. Initializing...")
            if self.alembic_dir.exists():
                logger.warning("Found existing alembic directory but missing configuration")
                self._cleanup_existing_alembic()
            self._initialize_alembic()
            logger.info("Alembic initialization complete")

    def _initialize_alembic(self) -> bool:
        """Initialize alembic structure and configuration"""
        try:
            # Ensure parent directory exists
            self.alembic_dir.parent.mkdir(exist_ok=True)

            # Run alembic init to create fresh directory structure
            # logger.info("Initializing alembic directory structure...")

            # Create initial config file for alembic init
            config_content = self._generate_alembic_ini_content()
            with open(self.alembic_ini_path, "w") as f:
                f.write(config_content)

            # Use the config we just created
            config = Config(str(self.alembic_ini_path))

            with redirect_stdout(io.StringIO()):
                command.init(config, str(self.alembic_dir))

            # Update script template after initialization
            self.update_script_template()

            # Update env.py with our customizations
            self._update_env_py(self.alembic_dir / "env.py")

            logger.info("Alembic initialization complete")
            return True

        except Exception as e:
            # Explicitly convert error to string
            logger.error(f"Failed to initialize alembic: {str(e)}")
            return False

    def _create_minimal_env_py(self, env_path: Path) -> None:
        """Creates a minimal env.py file for Alembic."""
        content = """
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from sqlmodel import SQLModel

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()"""

        with open(env_path, "w") as f:
            f.write(content)

    def _generate_alembic_ini_content(self) -> str:
        """
        Generates content for alembic.ini file.
        """
        engine_url = str(self.engine.url).replace("%", "%%")
        return f"""
[alembic]
script_location = {self.alembic_dir}
sqlalchemy.url = {engine_url}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""".strip()

    def update_script_template(self):
        """Update the Alembic script template to include SQLModel."""
        template_path = self.alembic_dir / "script.py.mako"
        try:
            with open(template_path, "r") as f:
                content = f.read()

            # Add sqlmodel import to imports section
            import_section = "from alembic import op\nimport sqlalchemy as sa"
            new_imports = "from alembic import op\nimport sqlalchemy as sa\nimport sqlmodel"

            content = content.replace(import_section, new_imports)

            with open(template_path, "w") as f:
                f.write(content)

            return True

        except Exception as e:
            logger.error(f"Failed to update script template: {e}")
            return False

    def _update_env_py(self, env_path: Path) -> None:
        """
        Updates the env.py file to use SQLModel metadata.
        """
        if not env_path.exists():
            self._create_minimal_env_py(env_path)
            return
        try:
            with open(env_path, "r") as f:
                content = f.read()

            # Add SQLModel import if not present
            if "from sqlmodel import SQLModel" not in content:
                content = "from sqlmodel import SQLModel\n" + content

            # Replace target_metadata
            content = content.replace("target_metadata = None", "target_metadata = SQLModel.metadata")

            # Update both configure blocks properly
            content = content.replace(
                """context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )""",
                """context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )""",
            )

            content = content.replace(
                """        context.configure(
                connection=connection, target_metadata=target_metadata
            )""",
                """        context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )""",
            )

            with open(env_path, "w") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to update env.py: {e}")
            raise

    # Fixed: use keyword-only argument

    def _ensure_alembic_setup(self, *, force: bool = False) -> None:
        """
        Ensures Alembic is properly set up, initializing if necessary.

        Args:
            force: If True, removes existing configuration and reinitializes
        """
        try:
            self._validate_alembic_setup()
            if force:
                logger.info("Force initialization requested. Cleaning up existing configuration...")
                self._cleanup_existing_alembic()
                self._initialize_alembic()
        except FileNotFoundError:
            logger.info("Alembic configuration not found. Initializing...")
            if self.alembic_dir.exists():
                logger.warning("Found existing alembic directory but missing configuration")
                self._cleanup_existing_alembic()
            self._initialize_alembic()
            logger.info("Alembic initialization complete")

    def _validate_alembic_setup(self) -> None:
        """Validates that Alembic is properly configured."""
        required_files = [self.alembic_ini_path, self.alembic_dir / "env.py", self.alembic_dir / "versions"]

        missing = [f for f in required_files if not f.exists()]
        if missing:
            raise FileNotFoundError(f"Alembic configuration incomplete. Missing: {', '.join(str(f) for f in missing)}")

    def get_alembic_config(self) -> Config:
        """
        Gets Alembic configuration.

        Returns:
            Config: Alembic Config object

        Raises:
            FileNotFoundError: If alembic.ini cannot be found
        """
        if not self.alembic_ini_path.exists():
            raise FileNotFoundError("Could not find alembic.ini")

        return Config(str(self.alembic_ini_path))

    def get_current_revision(self) -> Optional[str]:
        """
        Gets the current database revision.

        Returns:
            str: Current revision string or None if no revision
        """
        with self.engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()

    def get_head_revision(self) -> str:
        """
        Gets the latest available revision.

        Returns:
            str: Head revision string
        """
        config = self.get_alembic_config()
        script = ScriptDirectory.from_config(config)
        return script.get_current_head()

    def get_schema_differences(self) -> List[tuple]:
        """
        Detects differences between current database and models.

        Returns:
            List[tuple]: List of differences found
        """
        with self.engine.connect() as conn:
            context = MigrationContext.configure(conn)
            diff = compare_metadata(context, SQLModel.metadata)
            return list(diff)

    def check_schema_status(self) -> Tuple[bool, str]:
        """
        Checks if database schema matches current models and migrations.

        Returns:
            Tuple[bool, str]: (needs_upgrade, status_message)
        """
        try:
            current_rev = self.get_current_revision()
            head_rev = self.get_head_revision()

            if current_rev != head_rev:
                return True, f"Database needs upgrade: {current_rev} -> {head_rev}"

            differences = self.get_schema_differences()
            if differences:
                changes_desc = "\n".join(str(diff) for diff in differences)
                return True, f"Unmigrated changes detected:\n{changes_desc}"

            return False, "Database schema is up to date"

        except Exception as e:
            logger.error(f"Error checking schema status: {str(e)}")
            return True, f"Error checking schema: {str(e)}"

    def upgrade_schema(self, revision: str = "head") -> bool:
        """
        Upgrades database schema to specified revision.

        Args:
            revision: Target revision (default: "head")

        Returns:
            bool: True if upgrade successful
        """
        try:
            config = self.get_alembic_config()
            command.upgrade(config, revision)
            logger.info(f"Schema upgraded successfully to {revision}")
            return True

        except Exception as e:
            logger.error(f"Schema upgrade failed: {str(e)}")
            return False

    def check_and_upgrade(self) -> Tuple[bool, str]:
        """
        Checks schema status and upgrades if necessary.

        Returns:
            Tuple[bool, str]: (action_taken, status_message)
        """
        needs_upgrade, status = self.check_schema_status()

        if needs_upgrade:
            # Remove the auto_upgrade check since we explicitly called this method
            if self.upgrade_schema():
                return True, "Schema was automatically upgraded"
            else:
                return (
                    False,
                    "Automatic schema upgrade failed. You are seeing this message because there were differences in your current database schema and the most recent version of the Autogen Studio app database. You can ignore the error, or specifically, you can install AutoGen Studio in a new path `autogenstudio ui --appdir <new path>`.",
                )

        return False, status

    def generate_revision(self, message: str = "auto") -> Optional[str]:
        """
        Generates new migration revision for current schema changes.

        Args:
            message: Revision message

        Returns:
            str: Revision ID if successful, None otherwise
        """
        try:
            config = self.get_alembic_config()
            with redirect_stdout(io.StringIO()):
                command.revision(config, message=message, autogenerate=True)
                return self.get_head_revision()

        except Exception as e:
            logger.error(f"Failed to generate revision: {str(e)}")
            return None

    def get_pending_migrations(self) -> List[str]:
        """
        Gets list of pending migrations that need to be applied.

        Returns:
            List[str]: List of pending migration revision IDs
        """
        config = self.get_alembic_config()
        script = ScriptDirectory.from_config(config)

        current = self.get_current_revision()
        head = self.get_head_revision()

        if current == head:
            return []

        pending = []
        for rev in script.iterate_revisions(current, head):
            pending.append(rev.revision)

        return pending

    def print_status(self) -> None:
        """Prints current migration status information to logger."""
        current = self.get_current_revision()
        head = self.get_head_revision()
        differences = self.get_schema_differences()
        pending = self.get_pending_migrations()

        logger.info("=== Database Schema Status ===")
        logger.info(f"Current revision: {current}")
        logger.info(f"Head revision: {head}")
        logger.info(f"Pending migrations: {len(pending)}")
        for rev in pending:
            logger.info(f"  - {rev}")
        logger.info(f"Unmigrated changes: {len(differences)}")
        for diff in differences:
            logger.info(f"  - {diff}")

    def ensure_schema_up_to_date(self) -> bool:
        """
        Reset migrations and create fresh migration for current schema state.
        """
        try:
            logger.info("Resetting migrations and updating to current schema...")

            # 1. Clear the entire alembic directory
            if self.alembic_dir.exists():
                shutil.rmtree(self.alembic_dir)
                logger.info("Cleared alembic directory")

            # 2. Clear alembic_version table
            with self.engine.connect() as connection:
                connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
                connection.commit()
                logger.info("Reset alembic version")

            # 3. Reinitialize alembic from scratch
            if not self._initialize_alembic():
                logger.error("Failed to reinitialize alembic")
                return False

            # 4. Generate fresh migration from current schema
            revision = self.generate_revision("current_schema")
            if not revision:
                logger.error("Failed to generate new migration")
                return False
            logger.info(f"Generated fresh migration: {revision}")

            # 5. Apply the migration
            if not self.upgrade_schema():
                logger.error("Failed to apply migration")
                return False
            logger.info("Successfully applied migration")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure schema is up to date: {e}")
            return False
