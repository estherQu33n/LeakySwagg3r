import collections
import json
import re
import sys
import httpx
from colorama import Fore, Style
from httpx._urlparse import urlparse
from ratelimit import limits, sleep_and_retry

print(Fore.GREEN +
      '\n*********************************************************************************************\n'
      'Dear User, Thank you for using LeakySwagg3r ...\n'
      'This tool is meant for educational/pentest exercise by authorized person(s) only!\n\n\t' +
      '***As such, only use this tool if you are legally authorized to test a target***\n\n'.upper() +
      'The developer of this tool will NOT be held liable in case of any misuse of this tool!\n'
      '*********************************************************************************************' + Style.RESET_ALL)

print(Fore.CYAN + 'Usage:' + Style.RESET_ALL + Fore.YELLOW +
                  '\tTo disable SSL verification, use the \'--insecure\' argument:\n\n'
                  + Style.RESET_ALL + Fore.CYAN +
                  '\t$ python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema>\n'
                  '\t$ python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema> --insecure\n\n'
                  'Example:\n'
                  '\t$ python3 leakySwagg3r.py https://target.com/swagger.json\n'
                  '\t$ python3 leakySwagg3r.py http://backend.insecure.com/API/swagger/docs/v1 --insecure\n'
      + Style.RESET_ALL + Fore.GREEN +
      '*********************************************************************************************\n' + Style.RESET_ALL
      )

# define cmdline arguments
arg_names = ['script', 'swagger_endpoint', 'disableSSL']
args = dict(zip(arg_names, sys.argv))
list_of_args = collections.namedtuple('list_of_args', arg_names)
args = list_of_args(*(args.get(arg, None) for arg in arg_names))

# extract URL from arguments
endpoint = args[1]

# Specify timeout period
timeout = httpx.Timeout(10.0, read=30.0)


# Save the Swagger definition to file
def swagger_definition_file():
    if args[2] == '--insecure':
        url_resp = httpx.get(endpoint, verify=False)
    else:
        url_resp = httpx.get(endpoint)

    with open('swagger.json', 'w') as f:
        f.writelines(url_resp.text)
    content = open('swagger.json')
    content = json.load(content)
    return content


data = swagger_definition_file()


# extract the url from a given openAPI schema:
# (some openAPI endpoints have a way of specifying the API endpoint)
def find_if_base_path_exists():
    uri = urlparse(endpoint).scheme + '://' + urlparse(endpoint).netloc
    for key in data.keys():
        find_base_path = re.findall('basepath', key, flags=re.IGNORECASE)
        find_server_url = re.findall('servers', key, flags=re.IGNORECASE)
        if find_base_path:
            if data[key] == '/':
                uri = uri
            else:
                uri = uri + data[key]

        elif find_server_url:
            regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            if re.findall(regex, data[key][0]['url']):
                # replace localhost endpoint in schema with the domain if in prod
                if re.findall('localhost.*?', data[key][0]['url']):
                    localhost = urlparse(data[key][0]['url']).scheme + '://' + urlparse(data[key][0]['url']).netloc
                    uri = re.sub(localhost, uri, data[key][0]['url'])
                else:
                    uri = data[key][0]['url']
                # You can comment out the above if-else block if you want to run tests in local environment
                # Uncomment the below section
                # url = uri = data[key][0]['url']

            else:
                uri = uri + data[key][0]['url']
        else:
            uri = uri
    return uri


url = find_if_base_path_exists()


# There are so many ways openAPI schema is represented depending on the dev's choice
# As such, it is really tough (not impossible) to handle all of this
# This supported_schema() block will run if the specified endpoint schema conforms to this code,
# otherwise the unsupported_schema() block will be executed
def supported_schema():
    for path in data['paths']:
        for method in data['paths'][path]:
            num_of_requests = [key for key in data['paths'][path][method]]
            # Specify methods you wish to test
            allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']

            def format_path():
                m1 = re.findall(r'(/\{.*?})', path)
                if m1:
                    formatted_path = re.sub(r'(\{.*?})', '1', path)
                else:
                    formatted_path = re.sub(r'(\{.*?})', '', path)
                return formatted_path

            # Handle all other requests
            @sleep_and_retry
            @limits(calls=1, period=30)
            def all_other_endpoints():
                # Handle endpoints containing both parameters and a request body
                if 'parameters' in num_of_requests and 'requestBody' in num_of_requests:
                    # Handle parameter(s)
                    parameters = data['paths'][path][method]['parameters']
                    params = [
                        d['name'] + '=' + str(parameters[0]['schema']['$ref']) if '$ref' in parameters[0]['schema']
                        else d['name'] + '=' + parameters[0]['schema']['type'] if 'type' in parameters[0]['schema']
                        else d['name'] + '=' + str(list(parameters[0]['schema'].keys())[0])
                        for d in parameters]

                    # format endpoints with ID parameter, default set to 1
                    rams = [re.sub('=.*?$', '=1', k) if re.findall('.*?id=.*?', k, flags=re.IGNORECASE) else k
                            for k
                            in params]
                    payload = dict(i.split('=') for i in rams)

                    # Handle request body
                    for form in data['paths'][path][method]['requestBody']['content']:
                        if form == 'multipart/form-data':
                            if 'properties' in data['paths'][path][method]['requestBody']['content'][form]['schema']:
                                for file in data['paths'][path][method]['requestBody']['content'][form]['schema']['properties']:
                                    if file.lower() == 'file':
                                        d_data = '{\'' + file + '\': ' + '\'' + \
                                                 data['paths'][path][method]['requestBody']['content'][form]['schema'][
                                                     'properties'][file]['type'] + '\'}'
                                        path_without_curly = format_path()

                                        if method.upper() in allowed_methods:
                                            if args[2] == '--insecure':
                                                response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly,
                                                                         method=method, data=d_data)
                                            else:
                                                response = httpx.request(timeout=timeout, url=url + path_without_curly,
                                                                         method=method, data=d_data)

                                            unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                                      flags=re.IGNORECASE)
                                            if 200 >= response.status_code < 300 or response.status_code == 404:
                                                if unauthorized:
                                                    pass
                                                else:
                                                    print(Fore.GREEN + 'Potentially Unauthenticated:', Style.RESET_ALL,
                                                          Fore.RED, response.status_code, Style.RESET_ALL,
                                                          '\n', 'curl ' + '-X', method.upper(),
                                                          Fore.YELLOW + url + path_without_curly + Style.RESET_ALL,
                                                          '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                          '\'' + d_data + '\''
                                                          )
                            else:
                                # Just choosing the lazy path to send empty data
                                d_data = {}

                                path_without_curly = format_path()
                                if method.upper() in allowed_methods:
                                    if args[2] == '--insecure':
                                        response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly,
                                                                 method=method, data=d_data)
                                    else:
                                        response = httpx.request(timeout=timeout, url=url + path_without_curly,
                                                                 method=method, data=d_data)

                                    unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                              flags=re.IGNORECASE)
                                    if 200 >= response.status_code < 300 or response.status_code == 404:
                                        if unauthorized:
                                            pass
                                        else:
                                            print(Fore.GREEN + 'Potentially Unauthenticated:', Style.RESET_ALL,
                                                  Fore.RED, response.status_code, Style.RESET_ALL,
                                                  '\n', 'curl ' + '-X', method.upper(),
                                                  Fore.YELLOW + url + path_without_curly + Style.RESET_ALL,
                                                  '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                  '\'' + str(d_data) + '\''
                                                  )
                        elif form == 'application/json':
                            for key in data['paths'][path][method]['requestBody']['content'][form]['schema']:
                                if key == '$ref':
                                    schema = str(
                                        data['paths'][path][method]['requestBody']['content'][form]['schema'][key])
                                    schema = re.sub("#/", '', schema).split('/')
                                    for index, elm in enumerate(schema):
                                        if index < len(schema):
                                            formatter = '[\'{}\']'.format(elm)
                                            key += formatter
                                            _paths = eval(str(key).replace('$ref', 'data'))

                                            if index == len(schema) - 1:
                                                res = {}

                                                # check if 'properties' is in the request body
                                                if 'properties' in _paths:
                                                    for parameter in _paths['properties']:
                                                        if 'type' in _paths['properties'][parameter]:
                                                            res[parameter] = _paths['properties'][parameter][
                                                                'type']
                                                        elif '$ref' in _paths['properties'][parameter]:
                                                            res[parameter] = _paths['properties'][parameter]['$ref']
                                                        else:
                                                            res[parameter] = parameter
                                                else:
                                                    first_key = list(_paths.keys())[0]
                                                    res[first_key] = _paths[first_key]

                                                path_without_curly = format_path()

                                                if method.upper() in allowed_methods:
                                                    if args[2] == '--insecure':
                                                        response = httpx.request(timeout=timeout, verify=False, url=url +
                                                                                 path_without_curly,
                                                                                 method=method, data=res, params=payload)
                                                    else:
                                                        response = httpx.request(timeout=timeout, url=url + path_without_curly,
                                                                                 method=method, data=res, params=payload)
                                                    unauthorized = re.findall('^unauthorized.*true$',
                                                                              response.text,
                                                                              flags=re.IGNORECASE)

                                                    if 200 >= response.status_code < 300 or response.status_code == 404:
                                                        if unauthorized:
                                                            pass
                                                        else:
                                                            print(Fore.GREEN + 'Potentially Unauthenticated:', Style.RESET_ALL +
                                                                  Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                                                  'curl','-X', method.upper(), Fore.YELLOW + url +
                                                                  path_without_curly + '?' +
                                                                  '&'.join(rams).replace("integer","1").replace(
                                                                      "boolean", "True") + Style.RESET_ALL ,
                                                                  '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                                  '\'' +
                                                                  str(res) + '\''
                                                                  )

                # Handle paths with parameters only
                elif 'parameters' in num_of_requests:
                    parameters = data['paths'][path][method]['parameters']

                    if len(parameters) > 0:
                        # if 'schema' in 'parameters'
                        if 'schema' in parameters[0]:
                            params = [d['name'] + '=' + str(parameters[0]['schema']['$ref']) if '$ref' in parameters[0][
                                'schema']
                                      else d['name'] + '=' + parameters[0]['schema']['type'] if 'type' in parameters[0][
                                'schema']
                            else d['name'] + '=' + str(list(parameters[0]['schema'].keys())[0])
                                      for d in parameters]
                            rams = [re.sub('=.*?$', '=1', k) if
                                    re.findall('.*?id=.*?', k, flags=re.IGNORECASE) else
                                    k for k in params]

                            payload = dict(i.split('=') for i in rams)
                            path_without_curly = format_path()

                            if method.upper() in allowed_methods:
                                if args[2] == '--insecure':
                                    response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly, method=method,
                                                             params=payload)
                                else:
                                    response = httpx.request(timeout=timeout, url=url + path_without_curly, method=method,
                                                             params=payload)
                                unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                                if 200 >= response.status_code < 300 or response.status_code == 404:
                                    if unauthorized:
                                        pass
                                    else:
                                        print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                              Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                              'curl -X', method.upper(), Fore.YELLOW + url +
                                              path_without_curly + '?' +
                                              '&'.join(rams).replace("integer", "1").replace("boolean", "True") +
                                              Style.RESET_ALL
                                              )

                        elif 'type' in parameters[0]:
                            params = [d['name'] + '=' + parameters[0]['type'] for d in parameters]
                            rams = [
                                re.sub('=.*?$', '=1', k) if re.findall('.*?id=.*?', k, flags=re.IGNORECASE)
                                else k for k in params]
                            payload = dict(i.split('=') for i in rams)
                            path_without_curly = format_path()

                            if method.upper() in allowed_methods:
                                if args[2] == '--insecure':
                                    response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly, method=method,
                                                             params=payload)
                                else:
                                    response = httpx.request(timeout=timeout, url=url + path_without_curly, method=method, params=payload)

                                unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                                if 200 >= response.status_code < 300 or response.status_code == 404:
                                    if unauthorized:
                                        pass
                                    else:
                                        print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                              Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                              'curl -X', method.upper(), Fore.YELLOW + url + path_without_curly + '?' +
                                              '&'.join(rams).replace("integer", "1").replace("boolean", "True") +
                                              Style.RESET_ALL
                                              )

                        else:
                            params = [d['name'] + '=' + parameters[0]['name'] for d in parameters]
                            rams = [
                                re.sub('=.*?$', '=1', k) if re.findall('.*?id=.*?', k, flags=re.IGNORECASE)
                                else k for k in params]
                            payload = dict(i.split('=') for i in rams)
                            path_without_curly = format_path()

                            if method.upper() in allowed_methods:
                                if args[2] == '--insecure':
                                    response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly, method=method,
                                                             params=payload)
                                else:
                                    response = httpx.request(timeout=timeout, url=url + path_without_curly, method=method,
                                                             params=payload)

                                unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                                if 200 >= response.status_code < 300 or response.status_code == 404:
                                    if unauthorized:
                                        pass
                                    else:
                                        print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                              Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                              'curl -X', method.upper(), Fore.YELLOW + url + path_without_curly + '?' +
                                              '&'.join(rams).replace("integer", "1").replace("boolean", "True") +
                                              Style.RESET_ALL
                                              )
                    else:
                        path_without_curly = format_path()

                        if method.upper() in allowed_methods:
                            if args[2] == '--insecure':
                                response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly,
                                                         method=method)
                            else:
                                response = httpx.request(timeout=timeout, url=url + path_without_curly,
                                                         method=method)

                            unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                            if 200 >= response.status_code < 300 or response.status_code == 404:
                                if unauthorized:
                                    pass
                                else:
                                    print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                          Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                          'curl -X', method.upper(),
                                          Fore.YELLOW + url + path_without_curly + Style.RESET_ALL
                                          )

                # Handle paths with request body only
                elif 'requestBody' in num_of_requests:
                    for form in data['paths'][path][method]['requestBody']['content']:
                        if form == 'multipart/form-data':
                            if 'properties' in data['paths'][path][method]['requestBody']['content'][form]['schema']:
                                for file in data['paths'][path][method]['requestBody']['content'][form]['schema']['properties']:
                                    if file != 'keys':
                                        d_data = '{\'' + file + '\': ' + '\'' + \
                                                 data['paths'][path][method]['requestBody']['content'][form]['schema'][
                                                     'properties'][
                                                     file]['type'] + '\'}'
                                        path_without_curly = format_path()

                                        if method.upper() in allowed_methods:
                                            if args[2] == '--insecure':
                                                response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly,
                                                                         method=method, data=d_data)
                                            else:
                                                response = httpx.request(timeout=timeout, url=url + path_without_curly,
                                                                         method=method, data=d_data)

                                            unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                                      flags=re.IGNORECASE)
                                            if 200 >= response.status_code < 300 or response.status_code == 404:
                                                if unauthorized:
                                                    pass
                                                else:
                                                    print(Fore.GREEN + 'Potentially Unauthenticated:', Style.RESET_ALL,
                                                          Fore.RED, response.status_code, Style.RESET_ALL,
                                                          '\n', 'curl ' + '-X', method.upper(),
                                                          Fore.YELLOW + url + path_without_curly + Style.RESET_ALL,
                                                          '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                          '\'' + d_data + '\''
                                                          )
                            else:
                                # Just choosing the lazy path to send empty data
                                path_without_curly = format_path()
                                d_data = {}
                                if method.upper() in allowed_methods:
                                    if args[2] == '--insecure':
                                        response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly,
                                                                 method=method, data=d_data)
                                    else:
                                        response = httpx.request(timeout=timeout, url=url + path_without_curly,
                                                                 method=method, data=d_data)

                                    unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                              flags=re.IGNORECASE)
                                    if 200 >= response.status_code < 300 or response.status_code == 404:
                                        if unauthorized:
                                            pass
                                        else:
                                            print(Fore.GREEN + 'Potentially Unauthenticated:', Style.RESET_ALL,
                                                  Fore.RED, response.status_code, Style.RESET_ALL,
                                                  '\n', 'curl ' + '-X', method.upper(),
                                                  Fore.YELLOW + url + path_without_curly + Style.RESET_ALL,
                                                  '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                  '\'' + str(d_data) + '\''
                                                  )

                        elif form == 'application/json':
                            for key in data['paths'][path][method]['requestBody']['content'][form]['schema']:
                                if key == '$ref':
                                    schema = str(
                                        data['paths'][path][method]['requestBody']['content'][form]['schema'][key])
                                    schema = re.sub("#/", '', schema).split('/')
                                    for index, elm in enumerate(schema):
                                        if index < len(schema):
                                            formatter = '[\'{}\']'.format(elm)
                                            key += formatter
                                            _paths = eval(str(key).replace('$ref', 'data'))

                                            if index == len(schema) - 1:
                                                res = {}

                                                # Check if path contains 'parameters'
                                                if 'properties' in _paths:
                                                    for parameter in _paths['properties']:
                                                        if 'type' in _paths['properties'][parameter]:
                                                            res[parameter] = _paths['properties'][parameter][
                                                                'type']
                                                        elif '$ref' in _paths['properties'][parameter]:
                                                            res[parameter] = _paths['properties'][parameter]['$ref']
                                                        else:
                                                            res[parameter] = parameter
                                                    path_without_curly = format_path()
                                                    if method.upper() in allowed_methods:
                                                        if args[2] == '--insecure':
                                                            response = httpx.request(timeout=timeout, verify=False, url=url +
                                                                                     path_without_curly, method=method, data=res)
                                                        else:
                                                            response = httpx.request(timeout=timeout, verify=False, url=url +
                                                                                     path_without_curly,
                                                                                     method=method, data=res)

                                                        unauthorized = re.findall('^unauthorized.*true$',
                                                                                  response.text,
                                                                                  flags=re.IGNORECASE)

                                                        if 200 >= response.status_code < 300 or response.status_code == 404:
                                                            if unauthorized:
                                                                pass
                                                            else:
                                                                print(Fore.GREEN + 'Potentially Unauthenticated:',
                                                                      Style.RESET_ALL,
                                                                      Fore.RED, response.status_code,
                                                                      Style.RESET_ALL, '\n',
                                                                      'curl', '-X', method.upper(),
                                                                      Fore.YELLOW + url + path_without_curly + Style.RESET_ALL,
                                                                      '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                                      '\'' +
                                                                      str(res) + '\''
                                                                      )
                                                else:
                                                    first_key = list(_paths.keys())[0]
                                                    res[first_key] = _paths[first_key]

                                                    path_without_curly = format_path()

                                                    if method.upper() in allowed_methods:
                                                        response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly,
                                                                                 method=method, data=res)
                                                        unauthorized = re.findall('^unauthorized.*true$',
                                                                                  response.text,
                                                                                  flags=re.IGNORECASE)

                                                        if 200 >= response.status_code < 300 or response.status_code == 404:
                                                            if unauthorized:
                                                                pass
                                                            else:
                                                                print(Fore.GREEN + 'Potentially Unauthenticated:',
                                                                      Style.RESET_ALL,
                                                                      Fore.RED, response.status_code,
                                                                      Style.RESET_ALL, '\n',
                                                                      'curl ' + '-X', method.upper(),
                                                                      Fore.YELLOW + url + path_without_curly + Style.RESET_ALL,
                                                                      '-H', '\'Content-Type: ' + form + '\'', '-d',
                                                                      '\'' +
                                                                      str(res) + '\''
                                                                      )

            all_other_endpoints()

            # Handle endpoints without params or request body
            # Rate-limited calls
            @sleep_and_retry
            @limits(calls=1, period=30)
            def endpoints_without_params_nor_reqbody():
                if 'parameters' in num_of_requests or 'requestBody' in num_of_requests:
                    pass
                else:
                    path_without_curly = format_path()

                    if method.upper() in allowed_methods:
                        if args[2] == '--insecure':
                            response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly, method=method)
                        else:
                            response = httpx.request(timeout=timeout, url=url + path_without_curly, method=method)

                        unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                  flags=re.IGNORECASE)

                        if 200 >= response.status_code < 300 or response.status_code == 404:
                            if unauthorized:
                                pass
                            else:
                                print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                      Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                      'curl ' + '-X ' + method.upper(),
                                      Fore.YELLOW + url + path_without_curly + Style.RESET_ALL
                                      )

            endpoints_without_params_nor_reqbody()


# Handle all other requests where an exceptions is encountered
@sleep_and_retry
@limits(calls=1, period=30)
def unsupported_schema():
    for path in data['paths']:
        for method in data['paths'][path]:
            # Specify methods you wish to test
            allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']

            # Format path to remove curly braces
            def format_path():
                m1 = re.findall(r'(/\{.*?})', path)
                if m1:
                    formatted_path = re.sub(r'(\{.*?})', '1', path)
                else:
                    formatted_path = re.sub(r'(\{.*?})', '', path)
                return formatted_path

            path_without_curly = format_path()

            if method.upper() in allowed_methods:
                if args[2] == '--insecure':
                    response = httpx.request(timeout=timeout, verify=False, url=url + path_without_curly, method=method)
                else:
                    response = httpx.request(timeout=timeout, url=url + path_without_curly, method=method)
                unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                if 200 >= response.status_code < 300 or response.status_code == 404:
                    if unauthorized:
                        pass
                    else:
                        print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                              Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                              'curl -X', method.upper(), Fore.YELLOW + url +
                              path_without_curly + Style.RESET_ALL
                              )
            # Declare variables to be used later in exception block
            unsupported_schema.path = path
            unsupported_schema.method = method


# Instantiate a while loop to handle exceptions
while True:
    try:
        supported_schema()
        break
    except (TypeError, ValueError, KeyError, SyntaxError) as err:
        unsupported_schema()
        print('A {} error was encountered in path {} with method {}'.format(err, unsupported_schema.path, unsupported_schema.method))
    break


print(Fore.GREEN +
      '\n*********************************************************************************************\n'
      '\t\t\t\td0n3----&----dUst3d'
      '\n*********************************************************************************************'
      '\n' + Style.RESET_ALL
      )