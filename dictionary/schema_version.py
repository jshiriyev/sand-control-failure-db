"""Version of exported record content, separate from package/API versions.

Version 0 is intentionally mutable during development. When company data
collection begins, freeze the then-current shape as version 1 and preserve
its parser/validator when later incompatible versions are introduced.
"""
CURRENT_SCHEMA_VERSION = 0
