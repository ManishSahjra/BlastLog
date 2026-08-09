from database.db import connection


def add_user(empid, email, username, password):
    conn = connection()

    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO users(employee_id, email, username, password)
            VALUES(%s, %s, %s, %s)
            """

            cursor.execute(sql, (empid, email, username, password))

        conn.commit()

    finally:
        conn.close()


def get_user(username):
    conn = connection()

    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT *
            FROM users
            WHERE username = %s
            """

            cursor.execute(sql, (username,))

            return cursor.fetchone()

    finally:
        conn.close()


def add_blast_log(
    employee_id,
    blast_date,
    location,
    holes,
    depth,
    burden,
    spacing,
    explosives,
    volume,
    pf
):
    conn = connection()

    try:
        with conn.cursor() as cursor:
            query = """
            INSERT INTO blast_logs (
                employee_id,
                blast_date,
                location,
                holes,
                depth,
                burden,
                spacing,
                explosives,
                volume,
                pf
            )
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                employee_id,
                blast_date,
                location,
                holes,
                depth,
                burden,
                spacing,
                explosives,
                volume,
                pf
            )

            cursor.execute(query, values)

        conn.commit()

    finally:
        conn.close()


def get_blast_logs(employee_id):
    conn = connection()

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT *
            FROM blast_logs
            WHERE employee_id = %s
            ORDER BY blast_date
            """

            cursor.execute(query, (employee_id,))

            return cursor.fetchall()

    finally:
        conn.close()


def delete_blast_log(blast_id, employee_id):
    conn = connection()

    try:
        with conn.cursor() as cursor:
            query = """
            DELETE FROM blast_logs
            WHERE blast_id = %s
            AND employee_id = %s
            """

            cursor.execute(query, (blast_id, employee_id))

        conn.commit()

    finally:
        conn.close()


def get_dashboard_stats(employee_id):
    conn = connection()

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT
                COUNT(*) AS total_reports,
                COALESCE(SUM(volume), 0) AS total_explosive,
                COALESCE(AVG(pf), 0) AS avg_pf,
                COALESCE(SUM(holes), 0) AS total_holes,
                DATE_FORMAT(MAX(blast_date), '%%b') AS latest_month
            FROM blast_logs
            WHERE employee_id = %s
            """

            cursor.execute(query, (employee_id,))

            return cursor.fetchone()

    finally:
        conn.close()