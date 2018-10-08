# Templates
Templates are a powerful tool to guide your interaction with SU-lhcb-MC-gen.
While the suite itself is script-agnostic (meaning you can use it for anything,
not just MC generation), the templates provide easy-to-follow recipes for MC
generation (among other things) using SU-lhcb-MC-gen.

## How to use templates
To use a template, read its description (usually a docstring at the top of the
file) first; there may be guidance on how to use it or explanations of how it
works.

Copy it to a directory where you have write-access.

Search the file for statements enclosed by `<<<<` `>>>>` &mdash; these mark the
spots you need to edit in order for the script to work. (Make sure you overwrite
the `<<<<` `>>>>`. They are not part of the script.) If there are no `<<<<` or
`>>>>` left in the script, it's ready to use!

> If your editor supports RegEx searches, you can search for `<<<<.*>>>>`.

Just point `run_stages.py` or `submit_to_condor.py` (after testing &mdash; see
[../README.md](README.md)) at your edited configuration file. As always, _make
sure not to edit or move_ your configuration file while `submit_to_condor.py`
is running; this can result in your jobs changing behavior mid-stream.

> Note that templates are community-contributed and are _not_ guaranteed to work
> . You are responsible for your own code. Be especially careful to make sure
> you understand what you are doing if you make edits besides what is marked in
> the `<<<<` `>>>>`.

## Contributing templates
Contributions to the template library are encouraged. See
[CONTRIBUTING.md](CONTRIBUTING.md).
