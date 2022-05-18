# Nanome - Molecular surface with MSMS

A Nanome Plugin to run [MSMS](https://www.scripps.edu/sanner/html/msms_home.html) that computes molecular surfaces and load them in Nanome.
(Molecular Surface by Michael Sanner)

This plugin also computes Ambient Occlusion (AO) to darken buried parts of the molecular surfaces using https://github.com/nezix/AOEmbree

<img width="750" alt="MSMS Tab 1" src="https://user-images.githubusercontent.com/18257337/168937430-c9f116ba-8030-4823-9902-1b866839716c.png">
<img width="750" alt="MSMS Tab 2" src="https://user-images.githubusercontent.com/18257337/168937436-78f67adf-14e9-42a9-a062-40f29a171d0a.png">


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
