import sys
import os

# Add dashboards root to sys.path so office_requirements_dashboard
# and aquila_graphing_tools can be imported from there
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from office_requirements_dashboard import server as app  # noqa: F401 - Vercel WSGI entrypoint
