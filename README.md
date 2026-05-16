# MediConnect
Book your appointment with the doctor of your choice


# Command to update the existing doctor names
PS C:\Users\silpa\Downloads\MediConnect-MC_V1 (7)\MediConnect-MC_V1> python manage.py shell
21 objects imported automatically (use -v 2 for details).

Ctrl click to launch VS Code Native REPL
Python 3.12.0 (tags/v3.12.0:0fb18b0, Oct  2 2023, 13:03:39) [MSC v.1935 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> d = Doctor.objects.get(id=4)
>>> d.name = "Dr.Anjali"
>>> d.save()
>>> Doctor.objects.all().values("id","name")
<QuerySet [{'id': 2, 'name': 'Dr.Bhupatindra Narain Jha'}, {'id': 4, 'name': 'Dr.(Mrs) Munchun Jha'}]>
>>>            
