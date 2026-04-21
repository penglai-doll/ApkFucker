export function localizeExecutionFailureCode(code: string | null | undefined): string {
  switch (code) {
    case "app_install_error":
      return "安装样本失败";
    case "backend_not_configured":
      return "未配置真实后端";
    case "backend_unavailable":
      return "执行后端不可用";
    case "case_not_found":
      return "案件不存在";
    case "device_connect_failed":
      return "设备连接失败";
    case "frida_injection_error":
      return "Frida 注入失败";
    case "frida_runtime_unavailable":
      return "Frida 运行环境缺失";
    case "frida_script_error":
      return "Frida 脚本错误";
    case "frida_session_error":
      return "Frida 会话失败";
    case "validation_error":
      return "参数校验失败";
    case "unknown_execution_error":
      return "未知执行错误";
    default:
      return "暂无";
  }
}
