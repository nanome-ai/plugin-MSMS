# Nanome - Molecular surface with MSMS

A Nanome Plugin to run [MSMS](https://www.scripps.edu/sanner/html/msms_home.html) that computes molecular surfaces and load them in Nanome.
(Molecular Surface by Michael Sanner)

Optionally, this plugin computes Ambient Occlusion (AO) to darken buried parts of the molecular surfaces using https://github.com/nezix/AOEmbree


<img src="https://user-images.githubusercontent.com/9949327/143027625-b0ab5197-005e-49f9-9e31-6f8595d6800a.png" width="500"/>
<img src="https://user-images.githubusercontent.com/9949327/137134953-75b06353-2a60-44a2-9235-ee1589304da0.png" width="200"/>

## Dependencies

[Docker](https://docs.docker.com/get-docker/)
[Git LFS](https://git-lfs.github.com/)

## Usage

To run the plugin in a Docker container:

```sh
$ cd docker
$ ./build.sh
$ ./deploy.sh -a <plugin_server_address> [optional args]
```

## Development

After cloning, make sure LFS files are checked out.
```sh
git lfs fetch
git lfs checkout
```

To run the MSMS plugin with autoreload:

```sh
$ python3 -m pip install -r requirements.txt
$ python3 run.py -r -a <plugin_server_address> [optional args]
```

## License

MIT
