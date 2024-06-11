# LeakySwagg3r : 

- **This tool is meant to scan a Swagger(openAPI) target for unauthenticated endpoints**

- **All you need is an endpoint containing Swagger schema in json format eg https://target.com/openapi.json**

# Who can use this tool:
- Penetration Testers: Automatically scan a Swagger API for unauthenticated endpoints

- Developers: Automatically scan a Swagger API for any endpoints that aren't secured and potentially leaking sensitive information

- Bug Bounty Hunters: Test AUTHORIZED targets using openAPI for juicy unauthenticated endpoints

- Anyone Else: Try out this tool on AUTHORIZED targets only.

# Warning:

- **Before running this script, it is advisable to modify the allowed methods within the script first! i.e You may want to remove the DELETE method when testing a target in production environment!**

>***The developer of this tool will NOT be held liable in case of any misuse of this tool!***


# Usage:

SETUP:

	Linux: 
 
 		$ python3 -m pip install -r requirements.txt
   
	Windows: 
 
 		$ py -m pip install -r requirements.txt

USE:		

***Use optional argument '--insecure' to disable SSL certificate verification***

	Linux: 
 
		$ python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema>
  		$ python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema> --insecure
  
	Windows:
 
		$ py leakySwagg3r.py <endpoint_containing_swagger_json_schema>
  		$ py leakySwagg3r.py <endpoint_containing_swagger_json_schema> --insecure



EXAMPLE:

P/S: ***The specified endpoint must contain Swagger schema in json format***

	Linux: 
		$ python3 leakySwagg3r.py https://secure.target.com/API/swagger.json
  
		$ python3 leakySwagg3r.py http://insecure.target.com/openapi.json --insecure

 		$ python3 leakySwagg3r.py https://backend.target.com/v3/docs


# Sample Output:
![swagg3r](https://github.com/3sth3rN00n/LeakySwagg3r/assets/171611980/1210883d-a364-4160-8911-2ce33b991f5d)




