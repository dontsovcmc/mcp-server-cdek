"""MCP server for CDEK delivery service API."""

import sys

from dotenv import load_dotenv

__version__ = "0.6.0"

from .models import (  # noqa: E402, F401
    CdekBaseModel,
    City,
    Contact,
    DeliveryPoint,
    DeliveryRequest,
    EntityResponse,
    Error,
    IntakeRequest,
    Item,
    Location,
    Money,
    OrderInfo,
    OrderRef,
    OrderRequest,
    OrderUpdateRequest,
    Package,
    Phone,
    PrealertRequest,
    PrintRequest,
    Region,
    RequestStatus,
    Seller,
    Service,
    Status,
    Tariff,
    TariffRequest,
    TariffResult,
    Threshold,
    WebhookRequest,
)


def _load_env() -> None:
    """Load env from --env <path> if provided, otherwise use standard env."""
    for i, arg in enumerate(sys.argv):
        if arg == "--env" and i + 1 < len(sys.argv):
            load_dotenv(sys.argv[i + 1], override=True)
            sys.argv.pop(i)  # remove --env
            sys.argv.pop(i)  # remove <path>
            return


def main():
    _load_env()

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from .cli import main as cli_main
        cli_main()
    elif "--version" in sys.argv:
        print(f"mcp-server-cdek {__version__}")
    else:
        from .server import mcp
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
