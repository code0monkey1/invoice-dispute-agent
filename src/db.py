"""Compatibility import for the Supabase adapter during migration.

``src.db`` remains an alias of the adapter module so existing monkeypatches
and imports continue to affect the implementation's module globals.
"""

import sys

from src.adapters import supabase as _supabase

sys.modules[__name__] = _supabase
