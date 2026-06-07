from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0015_rename_current_health_problem_appointment_comments_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE appointments_appointment_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status varchar(10) NOT NULL,
                created_at datetime NOT NULL,
                doctor_id bigint NOT NULL,
                user_id integer NULL,
                slot_id bigint NOT NULL,
                amount decimal NOT NULL,
                consultation_type varchar(10) NOT NULL,
                payment_mode varchar(10) NOT NULL,
                booked_by_staff_id integer NULL,
                age integer NULL,
                comments text NULL,
                contact_number varchar(10) NULL,
                patient_name varchar(100) NOT NULL,
                payment_status varchar(10) NOT NULL
            );

            INSERT INTO appointments_appointment_new
            SELECT *
            FROM appointments_appointment;

            DROP TABLE appointments_appointment;

            ALTER TABLE appointments_appointment_new
            RENAME TO appointments_appointment;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]