import logging
from datetime import datetime
from pathlib import Path

# 日志配置

logger = logging.getLogger(__name__)

log_level = logging.INFO

logger.setLevel(log_level)

console_handler = logging.StreamHandler()

# 控制台日志级别
# console_handler.setLevel(logging.WARNING)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(filename)s(%(lineno)s): %(message)s")
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


def setup_log_file_handler():
    close_file_handler()
    # 创建一个文件处理器，并将日志写入指定的文件
    logs_path = Path(__file__).resolve().parent.parent / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)
    remove_log_by_create_time(logs_path)
    log_file = logs_path / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(log_level)

    file_handler.setFormatter(formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(file_handler)

    return logger


def close_file_handler(_logger=logger):
    """
    关闭日志处理器，释放文件
    :param _logger:
    :return:
    """
    for handler in _logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            _logger.removeHandler(handler)


def remove_log_by_create_time(log_dir: Path, count=10, suffix=".log") -> None:
    """
      判断log目录文件大于4个，按文件创建时间删除
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
        logger.error(f"文件路径参数不合法: {log_dir}")
        return
    if not p.exists():
        logger.error(f"文件路径不存在: {log_dir}")
        return
    # 获取全部 .log 后缀文件
    all_logs = [item for item in p.iterdir() if item.is_file() and item.suffix == suffix]
    # 按创建时间倒叙
    all_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    for item in all_logs[count:]:
        item.unlink()  # 删除多余的


logger = setup_log_file_handler()
