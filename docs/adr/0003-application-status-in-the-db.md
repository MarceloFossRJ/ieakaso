# Application status lives in the db, not in folders

The first design kept an Application's status as the folder its files sat in (`Applied` → `Interviewing` → `Not selected` / `Offer`). We dropped that: each Application's status is a field of its record in `db/ieakaso_db.json`, and its folder `output/applications/<application-id>/` never moves. A status that moves folders breaks every stored path to the Application's files (the db's own references, the Job ad's `**Also at:**` joins), and the applications tracker needs the status next to the other fields it shows and edits anyway.
