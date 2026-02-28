# HIS 医护人员操作手册

**版本**：1.0 | **细胞**：HIS

## 1. 患者与就诊

- 创建患者：POST /patients，Body：name、patientNo、gender、idNo（可选）、doctorId（可选）。返回脱敏姓名/身份证。
- 查询患者：GET /patients，请求头 X-User-Id 时仅返回该医生负责患者。
- 创建就诊：POST /visits，patientId、departmentId、doctorId。
- 挂号：POST /registration，patientId、departmentId、scheduleDate；幂等键 idempotentKey 或 X-Request-ID。

## 2. 处方与收费

- 开具处方：POST /prescriptions，visitId、drugList；同就诊同内容不可重复，否则返回「该就诊已存在相同处方」。
- 创建收费单：POST /charges，visitId、amountCents、idempotentKey（可选）。
- 缴费：POST /charges/<chargeId>/pay，Body：payCents。若仍有欠费，响应中带 message 与 arrearsCents 提示。

## 3. 住院与病历

- 住院登记：POST /inpatients，patientId、bedNo。
- 病历记录：POST /medical-records，patientId、visitId、content；仅追加，不可篡改。
