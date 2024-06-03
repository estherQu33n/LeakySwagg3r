# LeakySwagg3r
A Python tool to find misconfigured/unauthenticated Swagger API endpoints

This tool is meant for educational/pentest exercise by authorized person(s) only!
***As such, only use this tool if you are legally authorized to test a target***
      
The developer of this tool will NOT be held liable in case of any misuse of this tool!

SETUP:

	Unix: 
 
 		$ python3 -m pip install -r requirements.txt
   
	Windows: 
 
 		$ py -m pip install -r requirements.txt

USAGE:

	Unix: 
 
		$ python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema>
  
	Windows:
 
		$ py leakySwagg3r.py <endpoint_containing_swagger_json_schema>

EXAMPLE: 

	$ python3 leakySwagg3r.py https://localhost/swagger.json
