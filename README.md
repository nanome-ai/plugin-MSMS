# Nanome - Molecular surface with MSMS

A Nanome Plugin to run [MSMS](https://www.scripps.edu/sanner/html/msms_home.html) that computes molecular surfaces and load them in Nanome.
(Molecular Surface by Michael Sanner)

This plugin also computes Ambient Occlusion (AO) to darken buried parts of the molecular surfaces using https://github.com/nezix/AOEmbree


<img width="400" alt="MSMS Tab 1" src="https://user-images.githubusercontent.com/18257337/167722210-da109f46-be19-4fae-9f29-f4b54c46ab7d.png">
<img width="400" alt="MSMS Tab 2" src="https://user-images.githubusercontent.com/18257337/167722219-46fbc6cc-e388-4a1d-ba0c-2271da8f4ee3.png">

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
