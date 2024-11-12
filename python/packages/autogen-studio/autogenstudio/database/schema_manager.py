import os
from pathlib import Path
import shutil
from typing import Optional, Tuple, List
from loguru import logger
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.autogenerate import compare_metadata
from sqlalchemy import Engine
from sqlmodel import SQLModel


class SchemaManager:
    """
    Manages database schema validation and migrations using Alembic.
    Provides automatic schema validation, migrations, and safe upgrades.

    Args:
        engine: SQLAlchemy engine instance
        auto_upgrade: Whether to automatically upgrade schema when differences found
        init_mode: Controls initialization behavior:
            - "none": No automatic initialization (raises error if not set up)
            - "auto": Initialize if not present (default)
            - "force": Always reinitialize, removing existing configuration
    """

    def __init__(
        self,
        engine: Engine,
        auto_upgrade: bool = True,
        init_mode: str = "auto"
    ):
        if init_mode not in ["none", "auto", "force"]:
            raise ValueError("init_mode must be one of: none, auto, force")

        self.engine = engine
        self.auto_upgrade = auto_upgrade

        # Set up paths relative to this file
        self.base_dir = Path(__file__).parent
        self.alembic_dir = self.base_dir / 'alembic'
        self.alembic_ini_path = self.base_dir / 'alembic.ini'

        # Handle initialization based on mode
        if init_mode == "none":
            self._validate_alembic_setup()
        else:
            self._ensure_alembic_setup(force=init_mode == "force")

    def _cleanup_existing_alembic(self) -> None:
        """
        Safely removes existing Alembic configuration while preserving versions directory.
        """
        logger.info(
            "Cleaning up existing Alembic configuration while preserving versions...")

        # Create a backup of versions directory if it exists
        if self.alembic_dir.exists() and (self.alembic_dir / 'versions').exists():
            logger.info("Preserving existing versions directory")

        # Remove alembic directory contents EXCEPT versions
        if self.alembic_dir.exists():
            for item in self.alembic_dir.iterdir():
                if item.name != 'versions':
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                            logger.info(f"Removed directory: {item}")
                        else:
                            item.unlink()
                            logger.info(f"Removed file: {item}")
                    except Exception as e:
                        logger.error(f"Failed to remove {item}: {e}")

        # Remove alembic.ini if it exists
        if self.alembic_ini_path.exists():
            try:
                self.alembic_ini_path.unlink()
                logger.info(
                    f"Removed existing alembic.ini: {self.alembic_ini_path}")
            except Exception as e:
                logger.error(f"Failed to remove alembic.ini: {e}")

    def _ensure_alembic_setup(self, *, force: bool = False) -> None:
        """
        Ensures Alembic is properly set up, initializing if necessary.

        Args:
            force: If True, removes existing configuration and reinitializes
        """
        try:
            self._validate_alembic_setup()
            if force:
                logger.info(
                    "Force initialization requested. Cleaning up existing configuration...")
                self._cleanup_existing_alembic()
                self._initialize_alembic()
        except FileNotFoundError:
            logger.info("Alembic configuration not found. Initializing...")
            if self.alembic_dir.exists():
                logger.warning(
                    "Found existing alembic directory but missing configuration")
                self._cleanup_existing_alembic()
            self._initialize_alembic()
            logger.info("Alembic initialization complete")

    def _initialize_alembic(self) -> str:
        """Initializes Alembic configuration in the local directory."""
        logger.info("Initializing Alembic configuration...")

        # Check if versions exists
        has_versions = (self.alembic_dir / 'versions').exists()
        logger.info(f"Existing versions directory found: {has_versions}")

        # Create base directories
        self.alembic_dir.mkdir(exist_ok=True)
        if not has_versions:
            (self.alembic_dir / 'versions').mkdir(exist_ok=True)

        # Write alembic.ini
        ini_content = self._generate_alembic_ini_content()
        with open(self.alembic_ini_path, 'w') as f:
            f.write(ini_content)
        logger.info("Created alembic.ini")

        if not has_versions:
            # Only run init if no versions directory
            config = self.get_alembic_config()
            command.init(config, str(self.alembic_dir))
            logger.info("Initialized new Alembic directory structure")
        else:
            # Create minimal env.py if it doesn't exist
            env_path = self.alembic_dir / 'env.py'
            if not env_path.exists():
                self._create_minimal_env_py(env_path)
                logger.info("Created minimal env.py")
            else:
                # Update existing env.py
                self._update_env_py(env_path)
                logger.info("Updated existing env.py")

        logger.info(f"Alembic setup completed at {self.base_dir}")
        return str(self.alembic_ini_path)

    def _create_minimal_env_py(self, env_path: Path) -> None:
        """Creates a minimal env.py file for Alembic."""
        content = '''
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
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()'''

        with open(env_path, 'w') as f:
            f.write(content)

    def _generate_alembic_ini_content(self) -> str:
        """
        Generates content for alembic.ini file.
        """
        return f"""
[alembic]
script_location = {self.alembic_dir}
sqlalchemy.url = {self.engine.url}

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

    def _update_env_py(self, env_path: Path) -> None:
        """
        Updates the env.py file to use SQLModel metadata.
        """
        try:
            with open(env_path, 'r') as f:
                content = f.read()

            # Add SQLModel import
            if "from sqlmodel import SQLModel" not in content:
                content = "from sqlmodel import SQLModel\n" + content

            # Replace target_metadata
            content = content.replace(
                "target_metadata = None",
                "target_metadata = SQLModel.metadata"
            )

            # Add compare_type=True to context.configure
            if "context.configure(" in content and "compare_type=True" not in content:
                content = content.replace(
                    "context.configure(",
                    "context.configure(compare_type=True,"
                )

            with open(env_path, 'w') as f:
                f.write(content)

            logger.info("Updated env.py with SQLModel metadata")
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
                logger.info(
                    "Force initialization requested. Cleaning up existing configuration...")
                self._cleanup_existing_alembic()
                self._initialize_alembic()
        except FileNotFoundError:
            logger.info("Alembic configuration not found. Initializing...")
            if self.alembic_dir.exists():
                logger.warning(
                    "Found existing alembic directory but missing configuration")
                self._cleanup_existing_alembic()
            self._initialize_alembic()
            logger.info("Alembic initialization complete")

    def _validate_alembic_setup(self) -> None:
        """Validates that Alembic is properly configured."""
        if not self.alembic_ini_path.exists():
            raise FileNotFoundError("Alembic configuration not found")

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
        Checks schema status and upgrades if necessary (and auto_upgrade is True).

        Returns:
            Tuple[bool, str]: (action_taken, status_message)
        """
        needs_upgrade, status = self.check_schema_status()

        if needs_upgrade:
            if self.auto_upgrade:
                if self.upgrade_schema():
                    return True, "Schema was automatically upgraded"
                else:
                    return False, "Automatic schema upgrade failed"
            else:
                return False, f"Schema needs upgrade but auto_upgrade is disabled. Status: {status}"

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
            command.revision(
                config,
                message=message,
                autogenerate=True
            )
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
        Ensures the database schema is up to date, generating and applying migrations if needed.

        Returns:
            bool: True if schema is up to date or was successfully updated
        """
        try:
            # Check for unmigrated changes
            differences = self.get_schema_differences()
            if differences:
                # Generate new migration
                revision = self.generate_revision("auto-generated")
                if not revision:
                    return False
                logger.info(f"Generated new migration: {revision}")

            # Apply any pending migrations
            upgraded, status = self.check_and_upgrade()
            if not upgraded and "needs upgrade" in status.lower():
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to ensure schema is up to date: {e}")
            return False
