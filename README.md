# Nanome - MSMS

A Nanome Plugin to run MSMS to compute molecular surfaces and load it in Nanome.
(Molecular Surface by Michael Sanner)

Optionally computes AO (Ambient Occlusion) for the computed meshes using https://github.com/nezix/AOEmbree

![image](https://user-images.githubusercontent.com/9949327/137134953-75b06353-2a60-44a2-9235-ee1589304da0.png)

## Dependencies

[Docker](https://docs.docker.com/get-docker/)

## Usage

To run the plugin in a Docker container:

```sh
$ cd docker
$ ./build.sh
$ ./deploy.sh -a <plugin_server_address> [optional args]
```

## Development

To run the MSMS plugin with autoreload:

```sh
$ python3 -m pip install -r requirements.txt
$ python3 run.py -r -a <plugin_server_address> [optional args]
```

## License

MIT
