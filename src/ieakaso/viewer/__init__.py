"""The applications viewer: a Textual app to look at and edit the records of db/ieakaso_db.json.

It edits records, never creates or deletes them, and every write goes through the tracker module.
"""

from ieakaso.viewer.app import ViewerApp

__all__ = ["ViewerApp"]
