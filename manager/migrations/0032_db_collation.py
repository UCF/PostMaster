from django.db import migrations


def alter_collation(character_set, collation, schema_editor):
	with schema_editor.connection.cursor() as cursor:
		# set for database
		print('Altering database…')
		cursor.execute(
			f'ALTER DATABASE CHARACTER SET {character_set} COLLATE {collation};'
		)
		# set for tables (and convert data)
		cursor.execute(
			'SHOW TABLES;'
		)
		for table in cursor.fetchall():
			print(f'Altering table `{table}`…')
			cursor.execute(
				f'ALTER TABLE {table} CONVERT TO CHARACTER '
				f'SET {character_set} COLLATE {collation}'
			)


def alter_collation_forwards(apps, schema_editor):
	'''
	Sets *collation* and *character_set* for a database and its tables.
	Also converts data in the tables if necessary.
	'''
	return alter_collation('utf8mb4', 'utf8mb4_general_ci', schema_editor)


def alter_collation_reverse(apps, schema_editor):
	return alter_collation('latin1', 'latin1_swedish_ci', schema_editor)


class Migration(migrations.Migration):

	dependencies = [
		('manager', '0031_auto_20220111_1554'),
	]

	operations = [
		migrations.RunPython(alter_collation_forwards, alter_collation_reverse),
	]
