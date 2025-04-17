"""Скрипт для управления базой данных."""
import os
import sys

# Добавляем корневую директорию проекта в путь для импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import click
from sqlalchemy import create_engine
from database import Base
from config import current_config


@click.group()
def cli():
    """Утилиты для управления базой данных."""
    pass


@cli.command()
def init_db():
    """Инициализация базы данных."""
    engine = create_engine(current_config.DATABASE_URL)
    Base.metadata.create_all(engine)
    click.echo('База данных инициализирована')


@cli.command()
def clear_db():
    """Очистка базы данных."""
    engine = create_engine(current_config.DATABASE_URL)
    Base.metadata.drop_all(engine)
    click.echo('База данных очищена')


@cli.command()
def create_test_data():
    """Создание тестовых данных."""
    from tests.test_data import setup_test_data
    from database import Session
    
    session = Session()
    try:
        data = setup_test_data(session)
        click.echo('Тестовые данные созданы:')
        click.echo(f'Пользователь: {data["user"].username}')
        click.echo(f'Комната: {data["room"].code}')
        click.echo(f'Желание: {data["wish"].text}')
    finally:
        session.close()


@cli.command()
@click.argument('source')
@click.argument('destination')
def migrate_data(source, destination):
    """Миграция данных из одной базы в другую."""
    source_engine = create_engine(source)
    dest_engine = create_engine(destination)
    
    # Создаем таблицы в целевой базе
    Base.metadata.create_all(dest_engine)
    
    # Копируем данные
    with source_engine.connect() as source_conn, \
         dest_engine.connect() as dest_conn:
        for table in Base.metadata.tables.values():
            data = source_conn.execute(table.select()).fetchall()
            if data:
                dest_conn.execute(table.insert(), data)
    
    click.echo('Данные успешно перенесены')


if __name__ == '__main__':
    cli() 