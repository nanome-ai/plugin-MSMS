# Nanome - Molecular surface with MSMS

A Nanome Plugin to run [MSMS](https://www.scripps.edu/sanner/html/msms_home.html) that computes molecular surfaces and load them in Nanome.
(Molecular Surface by Michael Sanner)

This plugin also computes Ambient Occlusion (AO) to darken buried parts of the molecular surfaces using https://github.com/nezix/AOEmbree

<img width="750" alt="MSMS Tab 1" src="https://user-images.githubusercontent.com/18257337/173956361-406acd9e-7345-4807-994c-1192d18ef8c2.png">
<img width="750" alt="MSMS Tab 2" src="https://user-images.githubusercontent.com/18257337/173956360-58668ee2-1567-45b0-825d-b0c98dd31321.png">

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
