import os
import sys

import docker
import nginx


def start_containers(client, image, name):
    print("Starting up container : {}".format(name))
    client.containers.run(image, detach=True, name=name)


def reload_nginx(client):
    print("Reloading nginx")
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources")
    create_image(client, path, "reverseproxy")
    container = None
    try:
        container = client.containers.get("reverseproxy")
    except:
        print("nginx does not exists creating a new one")
    if container is not None:
        container.stop()
        container.remove()

    client.containers.run("reverseproxy:latest", ports={'80/tcp': '8080'},
                          name="reverseproxy")
    print("Reload of nginx successful")


def create_image(client, path, name):
    client.images.build(path=path, tag=name)


def modify_conf(contain_name):
    config = nginx.loadf(os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources/nginx.conf"))
    upstream = nginx.Upstream('docker-' + container_name, nginx.Key('server', 'tomcat:8080'))
    location = nginx.Location("/" + container_name, nginx.Key('rewrite', '^/' + container_name + '/(.*) /$1 break'),
                              nginx.Key('proxy_pass', 'http://docker-' + container_name + '/'),
                              nginx.Key('proxy_redirect', 'off'),
                              nginx.Key('proxy_set_header', 'Host $host'),
                              nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
                              nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
                              nginx.Key('proxy_set_header', 'X-Forwarded-Host $server_name'))
    for config_child in config.children:
        if isinstance(config_child, nginx.Http):
            new_http = config_child
            for http_child in config_child.children:
                if isinstance(http_child, nginx.Server):
                    new_http.remove(http_child)
                    new_server = http_child
                    new_server.add(location)
                    new_http.add(new_server)
                    break
            new_http.add(upstream)
            config.remove(config_child)
            config.add(new_http)
            break
    nginx.dumpf(config, os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources/nginx.conf"))


CONTAINER_IMG = "tomcat:alpine"
client = docker.from_env()
container_name = sys.argv[1]
print(container_name)
if container_name in client.containers.list():
    raise Exception('Container name already exist : {}'.format(container_name))
start_containers(client, CONTAINER_IMG, container_name)
modify_conf(container_name)
reload_nginx(client)
