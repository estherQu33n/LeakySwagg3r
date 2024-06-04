import json
import re
import sys
import httpx
from colorama import Fore, Style
from httpx._urlparse import urlparse
from ratelimit import limits, sleep_and_retry

endpoint = sys.argv[1]

print(Fore.GREEN +
      '******************************************************************************************\n'
      'Dear User, Thank you for using LeakySwagg3r ...\n'
      'This tool is meant for educational/pentest exercise by authorized person(s) only!\n'+
      '***As such, only use this tool if you are legally authorized to test a target***\n'.upper()+
      'The developer of this tool will NOT be held liable in case of any misuse of this tool!\n'
      '******************************************************************************************' + Style.RESET_ALL)

print(Fore.CYAN + 'Usage:\n\t python3 leakySwagg3r.py <endpoint_containing_swagger_json_schema>\n'
      'Example:\n\t python3 leakySwagg3r.py https://localhost/swagger.json\n'
      '\t python3 leakySwagg3r.py https://localhost/API/swagger/docs/v1\n'
      + Style.RESET_ALL + Fore.GREEN +
      '******************************************************************************************\n'+ Style.RESET_ALL
      )


def swagger_definition_file():
    url_resp = httpx.get(endpoint)
    with open('swagger.json', 'w') as f:
        f.writelines(url_resp.text)
    content = open('swagger.json')
    content = json.load(content)
    return content


data = swagger_definition_file()


def find_if_base_path_exists():
    uri = urlparse(endpoint).scheme+'://'+urlparse(endpoint).netloc
    for key in data.keys():
        find_base_path = re.findall('basepath', key, flags=re.IGNORECASE)
        if find_base_path:
            uri = uri + data[key]
        else:
            uri = uri
    return uri


url = find_if_base_path_exists()


def open_endpoints_scrapper():
    for path in data['paths']:
        for method in data['paths'][path]:
            num_of_requests = [key for key in data['paths'][path][method]]

            # Specify your methods to test
            allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']

            # Handle all other requests
            @sleep_and_retry
            @limits(calls=1, period=30)
            def all_other_endpoints():
                # Handle endpoints containing both parameters and a request body
                if 'parameters' in num_of_requests and 'requestBody' in num_of_requests:
                    # Handle parameter(s)
                    params = [d['name'] + '=' + d['schema']['type'] if 'type' in d['schema'] else
                              d['name'] + '=' + str(d['schema']['$ref'])
                              for d in data['paths'][path][method]['parameters']]

                    # format endpoints with ID parameter
                    # Default set to 100000000 to avoid accidentally tampering with an endpoint in PROD
                    # Imagine sending delete request to userID=1 where the user exists????
                    rams = [re.sub('=.*?$', '=100000000', k) if re.findall('.*?id=.*?', k, flags=re.IGNORECASE) else k for k
                            in params]
                    payload = dict(i.split('=') for i in rams)

                    # Handle request body
                    for form in data['paths'][path][method]['requestBody']:
                        for i in data['paths'][path][method]['requestBody'][form]:
                            if i == 'multipart/form-data':
                                for file in data['paths'][path][method]['requestBody'][form][i]['schema']['properties']:
                                    if file != 'keys':
                                        d_data = '{\'' + file + '\': ' + '\'' + \
                                                 data['paths'][path][method]['requestBody'][form][i]['schema'][
                                                     'properties'][file]['type'] + '\'}'
                                        path_without_curly = re.sub(r'(\{.*?})', '1', path)

                                        if method.upper() in allowed_methods:
                                            response = httpx.request(url=url + path_without_curly, method=method,
                                                                     data=d_data, params=payload)
                                            unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                                      flags=re.IGNORECASE)

                                            if 200 >= response.status_code < 300 or response.status_code == 404:
                                                if unauthorized:
                                                    pass
                                                else:
                                                    print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL +
                                                          Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                                          'curl ' + '-X', method.upper(), Fore.YELLOW + url +
                                                          path_without_curly + '?' +
                                                          '&'.join(rams).replace("integer", "1").replace("boolean",
                                                                                                         "True") + Style.RESET_ALL,
                                                          '-H', '\'Content-Type: ' + i + '\'', '-d',
                                                          '\'' + d_data + '\''
                                                          )
                            elif i == 'application/json':
                                for key in data['paths'][path][method]['requestBody'][form][i]['schema']:
                                    if key == '$ref':
                                        schema = str(
                                            data['paths'][path][method]['requestBody'][form][i]['schema'][key])
                                        schema = re.sub("#/", '', schema).split('/')
                                        for index, elm in enumerate(schema):
                                            if index < len(schema):
                                                formatter = '[\'{}\']'.format(elm)
                                                key += formatter
                                                _paths = eval(str(key).replace('$ref', 'data'))

                                                if index == len(schema) - 1:
                                                    res = {}
                                                    for parameter in _paths['properties']:
                                                        if 'type' in _paths['properties'][parameter]:
                                                            res[parameter] = _paths['properties'][parameter][
                                                                'type']
                                                        else:
                                                            res[parameter] = _paths['properties'][parameter][
                                                                '$ref']
                                                    path_without_curly = re.sub(r'(\{.*?})', '1', path)

                                                    if method.upper() in allowed_methods:
                                                        response = httpx.request(url=url + path_without_curly,
                                                                                 method=method, data=res,
                                                                                 params=payload)
                                                        unauthorized = re.findall('^unauthorized.*true$',
                                                                                  response.text,
                                                                                  flags=re.IGNORECASE)

                                                        if 200 >= response.status_code < 300 or response.status_code == 404:
                                                            if unauthorized:
                                                                pass
                                                            else:
                                                                print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL +
                                                                      Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                                                      'curl','-X', method.upper(), url + Fore.YELLOW+
                                                                      path_without_curly + '?' +
                                                                      '&'.join(rams).replace("integer","1").replace(
                                                                          "boolean", "True") + Style.RESET_ALL ,
                                                                      '-H', '\'Content-Type: ' + i + '\'', '-d',
                                                                      '\'' +
                                                                      str(res) + '\''
                                                                      )

                # Handle paths with parameters only
                elif 'parameters' in num_of_requests:
                    parameters = data['paths'][path][method]['parameters']

                    if len(parameters) > 0:
                        # if 'schema' in 'parameters'
                        if 'schema' in parameters[0]:
                            params = [d['name'] + '=' + str(parameters[0]['schema']['$ref']) if '$ref' in
                                      parameters[0]['schema'] else
                                      d['name'] + '=' + parameters[0]['schema']['type']
                                      for d in parameters]
                            rams = [re.sub('=.*?$', '=100000000', k) if
                                    re.findall('.*?id=.*?', k, flags=re.IGNORECASE) else
                                    k for k in params]
                            payload = dict(i.split('=') for i in rams)
                            path_without_curly = re.sub(r'(\{.*?})', '1', path)

                            if method.upper() in allowed_methods:
                                response = httpx.request(url=url + path_without_curly, method=method, params=payload)
                                unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                                if 200 >= response.status_code < 300 or response.status_code == 404:
                                    if unauthorized:
                                        pass
                                    else:
                                        print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                              Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                              'curl -X', method.upper(), Fore.YELLOW+ url +
                                              path_without_curly + '?' +
                                              '&'.join(rams).replace("integer", "1").replace("boolean", "True") +
                                              Style.RESET_ALL
                                              )

                        else:
                            params = [d['name'] + '=' + parameters[0]['type'] for d in parameters]
                            rams = [
                                re.sub('=.*?$', '=100000000', k) if re.findall('.*?id=.*?', k, flags=re.IGNORECASE)
                                else k for k in params]
                            payload = dict(i.split('=') for i in rams)
                            path_without_curly = re.sub(r'(\{.*?})', '1', path)

                            if method.upper() in allowed_methods:
                                response = httpx.request(url=url + path_without_curly, method=method, params=payload)
                                unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                                if 200 >= response.status_code < 300 or response.status_code == 404:
                                    if unauthorized:
                                        pass
                                    else:
                                        print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                              Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                              'curl -X', method.upper(), Fore.YELLOW+ url + path_without_curly + '?' +
                                              '&'.join(rams).replace("integer", "1").replace("boolean", "True")+
                                              Style.RESET_ALL
                                              )
                    else:
                        path_without_curly = re.sub(r'(\{.*?})', '1', path)

                        if method.upper() in allowed_methods:
                            response = httpx.request(url=url + path_without_curly, method=method)
                            unauthorized = re.findall('^unauthorized.*true$', response.text, flags=re.IGNORECASE)
                            if 200 >= response.status_code < 300 or response.status_code == 404:
                                if unauthorized:
                                    pass
                                else:
                                    print(Fore.GREEN + 'Potentially Unauthenticated:' + Style.RESET_ALL,
                                          Fore.RED + str(response.status_code) + Style.RESET_ALL, '\n',
                                          'curl -X', method.upper(), Fore.YELLOW+ url + path_without_curly + Style.RESET_ALL
                                          )

                # Handle paths with request body only
                elif 'requestBody' in num_of_requests:
                    for form in data['paths'][path][method]['requestBody']:
                        for i in data['paths'][path][method]['requestBody'][form]:
                            if i == 'multipart/form-data':
                                for file in data['paths'][path][method]['requestBody'][form][i]['schema']['properties']:
                                    if file != 'keys':
                                        d_data = '{\'' + file + '\': ' + '\'' + \
                                                 data['paths'][path][method]['requestBody'][form][i]['schema'][
                                                     'properties'][
                                                     file]['type'] + '\'}'
                                        path_without_curly = re.sub(r'(\{.*?})', '1', path)

                                        if method.upper() in allowed_methods:
                                            response = httpx.request(url=url + path_without_curly, method=method,
                                                                     data=d_data)
                                            unauthorized = re.findall('^unauthorized.*true$', response.text,
                                                                      flags=re.IGNORECASE)
                                            if 200 >= response.status_code < 300 or response.status_code == 404:
                                                if unauthorized:
                                                    pass
                                                else:
                                                    print(Fore.GREEN + 'Potentially Unauthenticated:', Style.RESET_ALL,
                                                          Fore.RED, response.status_code, Style.RESET_ALL,
                                                          '\n', 'curl ' + '-X', method.upper(),
                                                          Fore.YELLOW+ url + path_without_curly + Style.RESET_ALL,
                                                          '-H', '\'Content-Type: ' + i + '\'', '-d',
                                                          '\'' + d_data + '\''
                                                          )
                            elif i == 'application/json':
                                for key in data['paths'][path][method]['requestBody'][form][i]['schema']:
                                    if key == '$ref':
                                        schema = str(
                                            data['paths'][path][method]['requestBody'][form][i]['schema'][key])
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
                                                            else:
                                                                res[parameter] = _paths['properties'][parameter][
                                                                    '$ref']
                                                        path_without_curly = re.sub(r'(\{.*?})', '1', path)

                                                        if method.upper() in allowed_methods:
                                                            response = httpx.request(url=url + path_without_curly,
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
                                                                          'curl','-X', method.upper(),
                                                                          Fore.YELLOW+ url + path_without_curly + Style.RESET_ALL,
                                                                          '-H', '\'Content-Type: ' + i + '\'', '-d',
                                                                          '\'' +
                                                                          str(res) + '\''
                                                                          )
                                                    else:
                                                        res['type'] = _paths['type']
                                                        path_without_curly = re.sub(r'(\{.*?})', '1', path)

                                                        if method.upper() in allowed_methods:
                                                            response = httpx.request(url=url + path_without_curly,
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
                                                                          '-H', '\'Content-Type: ' + i + '\'', '-d',
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
                    path_without_curly = re.sub(r'(\{.*?})', '1', path)

                    if method.upper() in allowed_methods:
                        response = httpx.request(url=url + path_without_curly, method=method)
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


open_endpoints_scrapper()
