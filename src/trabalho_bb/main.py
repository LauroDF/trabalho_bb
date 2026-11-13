import asyncio
import signal
import sys


async def _run_application(module: str, *args: str) -> None:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        module,
        *args,
        start_new_session=True,
    )

    try:
        return_code = await process.wait()
        raise RuntimeError(
            f"{module} exited unexpectedly with status {return_code}"
        )
    finally:
        if process.returncode is None:
            process.send_signal(signal.SIGINT)
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await process.wait()


async def run() -> None:
    async with asyncio.TaskGroup() as task_group:
        # task_group.create_task(_run_application("trabalho_bb.hardware"))
        task_group.create_task(_run_application("trabalho_bb.routers.bank_router"))
        task_group.create_task(_run_application("trabalho_bb.web.server_rfid", "--proxy-only"))


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")


if __name__ == "__main__":
    main()
