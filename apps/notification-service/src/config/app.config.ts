import { APP_DEFAULTS, NodeEnv } from '@ai-recruit/common';
import { MicroserviceName } from '@ai-recruit/core';
import { registerAs } from '@nestjs/config';

export const getAppConfig = () => ({
  nodeEnv: process.env.NOTIFICATION_SERVICE_NODE_ENV || NodeEnv.Local,
  appName: process.env.NOTIFICATION_SERVICE_APP_NAME,
  appPort: +process.env.NOTIFICATION_SERVICE_APP_PORT || 3303,
  isProductionEnv: process.env.NOTIFICATION_SERVICE_NODE_ENV === NodeEnv.Production,
  frontendUrl: process.env.NOTIFICATION_SERVICE_FRONTEND_URL,
  queueDashboardPassword:
    process.env.NOTIFICATION_SERVICE_QUEUE_DASHBOARD_PASSWORD ||
    APP_DEFAULTS.QUEUE_DASHBOARD_PASSWORD,
  microserviceName: MicroserviceName.NotificationService,
});

export const appConfiguration = registerAs('app', getAppConfig);
