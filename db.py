import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.sql import func
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from datetime import datetime, timezone

SqlAlchemyBase = orm.declarative_base()

__factory: async_sessionmaker[AsyncSession] | None = None
__engine = None


class ArtistGenre(SqlAlchemyBase):
    __tablename__ = "artist_genres"
    artist_id = sa.Column(sa.String, primary_key=True)
    genres = sa.Column(sa.JSON, nullable=True)


class TrackCache(SqlAlchemyBase):
    __tablename__ = "track_cache"
    track_id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    album = sa.Column(sa.String, nullable=True)
    popularity = sa.Column(sa.Integer, nullable=True)
    duration_ms = sa.Column(sa.Integer, nullable=True)
    is_local = sa.Column(sa.Boolean, default=False)
    artist_id = sa.Column(sa.String, nullable=True)
    genres = sa.Column(sa.JSON, nullable=True)


class UsersHistory(SqlAlchemyBase):
    __tablename__ = "users_history"
    user_id = sa.Column(sa.String, primary_key=True)
    playlist_id = sa.Column(sa.String, primary_key=True)
    last_ref = sa.Column(sa.DateTime, nullable=True)


class PlaylistDataHistory(SqlAlchemyBase):
    __tablename__ = "playlist_data_history"
    playlist_id = sa.Column(sa.String, primary_key=True)
    playlist_name = sa.Column(sa.String, nullable=True)
    playlist_data = sa.Column(sa.String, nullable=True)


async def db_init(db_file):
    global __factory, __engine

    if __factory is not None:
        return

    if len(db_file) == 0:
        raise Exception("Необходимо указать файл базы данных.")

    conn_str = f"sqlite+aiosqlite:///{db_file}"
    __engine = create_async_engine(conn_str, echo=False, future=True, connect_args={"timeout": 30}) # 30 секунд при конфликте блокировок
    __factory = async_sessionmaker(bind=__engine, expire_on_commit=False, class_=AsyncSession)

    async with __engine.begin() as conn:
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


def create_session():
    global __factory
    if __factory is None:
        raise Exception("База данных не инициализирована.")
    return __factory()


async def add_playlist_data(session, playlist_data, playlist_id, playlist_name):
    row = await session.scalar(select(PlaylistDataHistory).where(PlaylistDataHistory.playlist_id == playlist_id))
    if row is None:
        session.add(PlaylistDataHistory(playlist_id=playlist_id, playlist_data=playlist_data, playlist_name=playlist_name))
    else:
        row.playlist_data = playlist_data
        row.playlist_name = playlist_name


async def save_user_history(session, user_id, playlist_id):
    row = await session.scalar(select(UsersHistory).where(and_(UsersHistory.user_id == user_id, UsersHistory.playlist_id == playlist_id)))
    now = datetime.now(timezone.utc)
    ref_max_count = 10
    if row is None:
        session.add(UsersHistory(user_id=user_id, playlist_id=playlist_id, last_ref=now))
        count = await session.scalar(select(func.count(UsersHistory.user_id)).where(UsersHistory.user_id == user_id))
        if count > ref_max_count:
            await session.execute(delete(UsersHistory).where(and_(UsersHistory.user_id == user_id, UsersHistory.last_ref == select(func.min(UsersHistory.last_ref)).where(UsersHistory.user_id == user_id).scalar_subquery())))
    else:
        row.last_ref = now


async def get_user_history(session, user_id):
    result = await session.execute(
        select(UsersHistory.playlist_id, PlaylistDataHistory.playlist_name)
        .join(PlaylistDataHistory, UsersHistory.playlist_id == PlaylistDataHistory.playlist_id)
        .where(UsersHistory.user_id == user_id)
    )
    return {row.playlist_name: row.playlist_id for row in result.all()}


async def get_playlist_history(session, playlist_id):
    row = await session.scalar(select(PlaylistDataHistory).where(PlaylistDataHistory.playlist_id == playlist_id))
    return row.playlist_data if row else None


async def get_artist_genres_cached(session, artist_id):
    row = await session.scalar(select(ArtistGenre).where(ArtistGenre.artist_id == artist_id))
    return row.genres if row else None


async def set_artist_genres_cached(session, artist_id, genres):
    row = await session.scalar(select(ArtistGenre).where(ArtistGenre.artist_id == artist_id))
    if row:
        row.genres = genres
    else:
        session.add(ArtistGenre(artist_id=artist_id, genres=genres))


async def cache_track(session, track_dict, artist_genres):
    track_id = track_dict.get("id")
    if not track_id:
        return

    row = await session.scalar(select(TrackCache).where(TrackCache.track_id == track_id))

    album_name = track_dict["album"]["name"]
    artist_id = track_dict["artists"][0]["id"]

    data = dict(
        track_id=track_id,
        name=track_dict.get("name"),
        album=album_name,
        popularity=track_dict.get("popularity"),
        duration_ms=track_dict.get("duration_ms"),
        is_local=bool(track_dict.get("is_local",   False)),
        artist_id=artist_id,
        genres=artist_genres,
    )

    if row:
        for key, val in data.items():
            setattr(row, key, val)
    else:
        session.add(TrackCache(**data))
