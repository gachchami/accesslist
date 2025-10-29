# AccessList

**AccessList** is a Flask app that demonstrates a snapshot of a resource-sharing scenario.

---

## Environment

This was run under **Python 3.14.0**.

### Install dependencies

```bash
pip install -r requirements.txt --no-cache
```

---

## Run the Flask App

This is a blocking command, so use a separate terminal to call the APIs:

```bash
python app.py
```

---

## Reset the Database

Run the following to reset the DB:

```bash
rm instance/acl.db
bash init.sh
python sample_data.py
```
