import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


def remove_log_by_create_time(log_dir: Path,  count=8, suffix='.log') -> None:
    """
      判断log目录文件大于8个，按文件创建时间删除
    :param log_dir: log日志目录
    :param count: 保留log文件数量
    :param suffix: 查找log文件后缀
    :return: None
    """
    if isinstance(log_dir, Path):
        p = log_dir
    elif isinstance(log_dir, str):
        p = Path(log_dir)
    else:
        log.error(f"文件路径参数不合法: {log_dir}")
        return
    if not p.exists():
        log.error(f"文件路径不存在: {log_dir}")
        return
    # 获取全部 .log 后缀文件
    all_logs = [item for item in p.iterdir() if item.is_file() and item.suffix == suffix]
    # 按创建时间倒叙
    all_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    for item in all_logs[count:]:
        item.unlink()  # 删除多余的


def set_log_format(config):
    """设置 log 日志格式"""
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 只保留最近 5 个 log 文件
    remove_log_by_create_time(log_dir=Path(config.rootdir).joinpath('logs'))
    # log_file default log file name
    if not config.getini('log_file') and not config.getoption('log_file'):
        config.option.log_file = Path(config.rootdir).joinpath('logs', f'{current_time}.log')
    if not config.getini('log_file_level') and not config.getoption('log_file_level'):
        config.option.log_file_level = "info"
    if config.getini('log_file_format') == '%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s' \
            and not config.getoption('log_file_format'):
        config.option.log_file_format = "%(asctime)s [%(levelname)s]: %(message)s"
    if config.getini('log_file_date_format') == '%H:%M:%S' and not config.getoption('log_file_date_format'):
        config.option.log_file_date_format = "%Y-%m-%d %H:%M:%S"
    # 设置 日志文件在控制台的输出格式
    if not config.getini('log_cli_format') and not config.getoption('log_cli_format'):
        config.option.log_cli_format = '%(asctime)s [%(levelname)s]: %(message)s'
    if not config.getini('log_cli_date_format') and not config.getoption('log_cli_date_format'):
        config.option.log_cli_date_format = '%Y-%m-%d %H:%M:%S'
    return current_time
