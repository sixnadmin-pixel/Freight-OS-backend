from psycopg import sql

def build_insert(table: str, data: dict, returning: str = "*"):
    cols = sql.SQL(", ").join(sql.Identifier(c) for c in data)
    vals = sql.SQL(", ").join(sql.Placeholder(c) for c in data)
    return sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
        sql.Identifier(table),
        cols,
        vals,
        sql.SQL(returning),
    )