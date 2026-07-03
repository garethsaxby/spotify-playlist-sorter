"""Command-line interface: ``login`` and ``sort`` commands."""

from __future__ import annotations

import argparse
from dataclasses import replace
from typing import TYPE_CHECKING

from . import auth, config, display
from .reccobeats import ReccoBeatsClient, ReccoBeatsError
from .sorter import build_proposed_order
from .spotify import SpotifyClient, SpotifyError, parse_playlist_id

if TYPE_CHECKING:
    from .models import AudioFeatures, ProposedOrder, SourcePlaylist, Track

_MIN_TRACKS = 2

_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_BAD_INPUT = 2
_EXIT_NOT_AUTH = 3
_EXIT_NOT_OWNED = 4
_EXIT_NOTHING_SORTABLE = 5
_EXIT_WRITE_FAILED = 6
_EXIT_TOO_FEW = 7


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=config.APP_NAME,
        description="Sort a Spotify playlist by Camelot key then BPM.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("login", help="Authenticate with Spotify")
    sort_parser = sub.add_parser("sort", help="Preview and write a sorted playlist")
    sort_parser.add_argument("playlist", help="Spotify playlist URL, URI, or id")
    sort_parser.add_argument(
        "--yes", action="store_true", help="Skip the confirmation prompt"
    )
    sort_parser.add_argument("--name", help="Name for the new playlist")
    sort_parser.add_argument(
        "--public", action="store_true", help="Make the new playlist public"
    )
    return parser


def _cmd_login() -> int:
    try:
        client_id = config.client_id()
    except ValueError as error:
        display.message(f"[red]{error}[/]")
        return _EXIT_ERROR
    try:
        granted = auth.login(client_id)
    except (auth.AuthError, OSError) as error:
        display.message(f"[red]Login failed: {error}[/]")
        return _EXIT_ERROR
    display.message("[green]Logged in. Token cached.[/]")
    display.message(f"[dim]Granted scopes: {granted or '(none reported)'}[/]")
    return _EXIT_OK


def _with_features(track: Track, features: dict[str, AudioFeatures]) -> Track:
    found = features.get(track.spotify_id)
    if found is None:
        return track
    return replace(track, features=found)


def _write_playlist(
    args: argparse.Namespace,
    source: SourcePlaylist,
    order: ProposedOrder,
    spotify: SpotifyClient,
) -> int:
    name = args.name or f"{source.name} (Camelot sorted)"
    try:
        new = spotify.create_playlist(name, public=bool(args.public))
    except SpotifyError as error:
        display.message(
            f"[red]Could not create playlist: {error}. Source unchanged.[/]"
        )
        return _EXIT_WRITE_FAILED
    try:
        spotify.add_tracks(new.playlist_id, [track.uri for track in order.ordered])
    except SpotifyError as error:
        display.message(
            f"[red]Failed to fill '{new.name}' ({new.url}): {error}. "
            f"Source unchanged; you may delete the incomplete playlist.[/]"
        )
        return _EXIT_WRITE_FAILED
    display.message(
        f"[green]Created '{new.name}': {len(order.sortable)} sorted, "
        f"{len(order.unsortable)} unsorted -> {new.url}[/]"
    )
    return _EXIT_OK


def _run_sort(
    args: argparse.Namespace,
    playlist_id: str,
    spotify: SpotifyClient,
    recco: ReccoBeatsClient,
) -> int:
    user_id = spotify.current_user_id()
    source = spotify.get_playlist(playlist_id)
    if source.owner_id != user_id:
        display.message("[red]You can only sort playlists you own.[/]")
        return _EXIT_NOT_OWNED
    if len(source.tracks) < _MIN_TRACKS:
        display.message("Nothing to sort (playlist has fewer than 2 tracks).")
        return _EXIT_TOO_FEW
    features = recco.fetch_features([track.spotify_id for track in source.tracks])
    tracks = [_with_features(track, features) for track in source.tracks]
    order = build_proposed_order(tracks)
    if not order.sortable:
        display.message("[yellow]No track had a determinable key/BPM.[/]")
        return _EXIT_NOTHING_SORTABLE
    display.render_order(order)
    if not (args.yes or display.confirm("Create new sorted playlist?")):
        display.message("No changes made.")
        return _EXIT_OK
    return _write_playlist(args, source, order, spotify)


def _cmd_sort(args: argparse.Namespace) -> int:
    try:
        playlist_id = parse_playlist_id(args.playlist)
    except ValueError as error:
        display.message(f"[red]{error}[/]")
        return _EXIT_BAD_INPUT
    session = auth.load_session()
    if session is None:
        display.message("[red]Not logged in. Run the `login` command first.[/]")
        return _EXIT_NOT_AUTH
    spotify = SpotifyClient(session.access_token)
    recco = ReccoBeatsClient()
    try:
        return _run_sort(args, playlist_id, spotify, recco)
    except (SpotifyError, ReccoBeatsError, auth.AuthError) as error:
        display.message(f"[red]{error}[/]")
        return _EXIT_ERROR
    finally:
        spotify.close()
        recco.close()


def main(argv: list[str] | None = None) -> int:
    """Return the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "login":
        return _cmd_login()
    if args.command == "sort":
        return _cmd_sort(args)
    parser.print_help()
    return _EXIT_OK
