# LeakySwagg3r : ***Your Swagger API Pentest Tool***
# Warning:
***This tool is meant for educational/pentest exercise by authorized person(s) only!
As such, only use this tool if you are legally authorized to test a target***  

***[Warning]:***

***Before running the script, It is advisable to modify the allowed methods in the script first! i.e You may want to remove DELETE when testing production environments***

# The developer of this tool will NOT be held liable in case of any misuse of this tool!
------------------------------------------------------------------------------------------------------


SETUP:

	Linux: 
 
 		$ python3 -m pip install -r requirements.txt
   
	Windows: 
 
 		$ py -m pip install -r requirements.txt

USAGE:

	Linux: 
 
		$ python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema>
  
	Windows:
 
		$ py leakySwagg3r.py <endpoint_containing_swagger_json_schema>

EXAMPLE: 

	$ python3 leakySwagg3r.py https://localhost/swagger.json

=======
![swagger_0](https://github.com/3sth3rN00n/LeakySwagg3r/assets/171611980/6413f8d5-3674-4093-a880-045df328054c)
