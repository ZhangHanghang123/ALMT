import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, InputNumber, Space, message, Popconfirm, Row, Col, Card, Tag, Divider } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

interface CurveDefinition {
  id: number
  uuid: string
  curve_code: string
  curve_name: string
  curve_type: string
  currency: string
  description: string
  is_active: number
  remark: string
}

interface CurvePoint {
  id: number
  uuid: string
  curve_uuid: string
  term: string
  term_days: number
  rate_value: number
  spread: number
  is_active: number
  remark: string
}

const CURVE_TYPES = [
  { value: 'SHIBOR', label: '银行间同业拆借利率' },
  { value: '国债', label: '国债收益率' },
  { value: 'LPR', label: '贷款市场报价利率' },
  { value: 'FTP', label: '内部资金转移定价' },
  { value: '存贷', label: '存贷款利率' },
  { value: '其他', label: '其他' }
]

const CurvePage: React.FC = () => {
  const [definitions, setDefinitions] = useState<CurveDefinition[]>([])
  const [selectedCurve, setSelectedCurve] = useState<CurveDefinition | null>(null)
  const [points, setPoints] = useState<CurvePoint[]>([])
  const [loading, setLoading] = useState(false)
  const [defModalVisible, setDefModalVisible] = useState(false)
  const [pointModalVisible, setPointModalVisible] = useState(false)
  const [editingDef, setEditingDef] = useState<CurveDefinition | null>(null)
  const [editingPoint, setEditingPoint] = useState<CurvePoint | null>(null)
  const [curveTypeOptions, setCurveTypeOptions] = useState<{value: string, label: string}[]>([])
  const [defForm] = Form.useForm()
  const [pointForm] = Form.useForm()

  // 加载曲线定义列表
  const fetchDefinitions = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/curve/definitions')
      const data = Array.isArray(res.data) ? res.data : []
      setDefinitions(data)
      // 动态生成曲线类型选项（从已有的curve_type中提取）
      const types = [...new Set(data.map((d: CurveDefinition) => d.curve_type).filter(Boolean))]
      setCurveTypeOptions([
        { value: '', label: '请选择类型' },
        ...types.map((t: string) => ({ value: t, label: t }))
      ])
    } catch (e) {
      message.error('加载曲线定义失败')
    } finally {
      setLoading(false)
    }
  }

  // 加载曲线点
  const fetchPoints = async (curveUuid: string) => {
    try {
      const res = await apiClient.get('/curve/points', { params: { curve_uuid: curveUuid } })
      setPoints(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      message.error('加载曲线点失败')
    }
  }

  useEffect(() => {
    fetchDefinitions()
  }, [])

  // 选择曲线
  const handleSelectCurve = (record: CurveDefinition) => {
    setSelectedCurve(record)
    fetchPoints(record.uuid)
  }

  // 曲线定义列
  const defColumns = [
    { title: '曲线代码', dataIndex: 'curve_code', key: 'curve_code', width: 120, fixed: 'left' as const },
    { title: '曲线名称', dataIndex: 'curve_name', key: 'curve_name', width: 180, ellipsis: true },
    { title: '曲线类型', dataIndex: 'curve_type', key: 'curve_type', width: 100,
      render: (v: string) => <Tag color="blue">{v || '-'}</Tag>
    },
    { title: '币种', dataIndex: 'currency', key: 'currency', width: 70 },
    { title: '描述', dataIndex: 'description', key: 'description', width: 200, ellipsis: true },
    { title: '操作', key: 'action', width: 100, fixed: 'right' as const,
      render: (_: any, r: CurveDefinition) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEditDef(r)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDeleteDef(r.uuid)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  // 曲线点列
  const pointColumns = [
    { title: '期限', dataIndex: 'term', key: 'term', width: 80, fixed: 'left' as const },
    { title: '期限(天)', dataIndex: 'term_days', key: 'term_days', width: 90 },
    { title: '利率(%)', dataIndex: 'rate_value', key: 'rate_value', width: 100,
      render: (v: number) => v != null ? (Number(v) * 100).toFixed(4) + '%' : '-'
    },
    { title: '利差(BP)', dataIndex: 'spread', key: 'spread', width: 100,
      render: (v: number) => v != null ? (Number(v) * 10000).toFixed(0) : '-'
    },
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 150, ellipsis: true },
    { title: '操作', key: 'action', width: 80,
      render: (_: any, r: CurvePoint) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEditPoint(r)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDeletePoint(r.uuid)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  // 新增曲线定义
  const handleAddDef = () => {
    setEditingDef(null)
    defForm.resetFields()
    setDefModalVisible(true)
  }

  // 编辑曲线定义
  const handleEditDef = (record: CurveDefinition) => {
    setEditingDef(record)
    defForm.setFieldsValue(record)
    setDefModalVisible(true)
  }

  // 保存曲线定义
  const handleSaveDef = async () => {
    try {
      const values = await defForm.validateFields()
      if (editingDef) {
        await apiClient.put(`/curve/definitions/${editingDef.uuid}`, values)
        message.success('更新成功')
      } else {
        await apiClient.post('/curve/definitions', values)
        message.success('创建成功')
      }
      setDefModalVisible(false)
      fetchDefinitions()
    } catch (e: any) {
      message.error(e.response?.data?.detail || '保存失败')
    }
  }

  // 删除曲线定义
  const handleDeleteDef = async (uuid: string) => {
    try {
      await apiClient.delete(`/curve/definitions/${uuid}`)
      message.success('删除成功')
      if (selectedCurve?.uuid === uuid) {
        setSelectedCurve(null)
        setPoints([])
      }
      fetchDefinitions()
    } catch (e) {
      message.error('删除失败')
    }
  }

  // 新增曲线点
  const handleAddPoint = () => {
    if (!selectedCurve) {
      message.warning('请先选择曲线')
      return
    }
    setEditingPoint(null)
    pointForm.resetFields()
    pointForm.setFieldsValue({ curve_uuid: selectedCurve.uuid })
    setPointModalVisible(true)
  }

  // 编辑曲线点
  const handleEditPoint = (record: CurvePoint) => {
    setEditingPoint(record)
    pointForm.setFieldsValue(record)
    setPointModalVisible(true)
  }

  // 保存曲线点
  const handleSavePoint = async () => {
    try {
      const values = await pointForm.validateFields()
      if (editingPoint) {
        await apiClient.put(`/curve/points/${editingPoint.uuid}`, values)
        message.success('更新成功')
      } else {
        await apiClient.post('/curve/points', values)
        message.success('创建成功')
      }
      setPointModalVisible(false)
      if (selectedCurve) {
        fetchPoints(selectedCurve.uuid)
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || '保存失败')
    }
  }

  // 删除曲线点
  const handleDeletePoint = async (uuid: string) => {
    try {
      await apiClient.delete(`/curve/points/${uuid}`)
      message.success('删除成功')
      if (selectedCurve) {
        fetchPoints(selectedCurve.uuid)
      }
    } catch (e) {
      message.error('删除失败')
    }
  }

  return (
    <div style={{ padding: '0 24px' }}>
      <Row gutter={16} style={{ height: 'calc(100vh - 140px)' }}>
        {/* 左侧：曲线定义列表 */}
        <Col span={10} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Card
            title="曲线定义"
            extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleAddDef}>新增</Button>}
            bodyStyle={{ padding: 0, flex: 1, overflow: 'auto' }}
            style={{ height: '100%' }}
          >
            <Table
              columns={defColumns}
              dataSource={definitions}
              rowKey="id"
              loading={loading}
              size="small"
              pagination={false}
              scroll={{ y: 'calc(100vh - 220px)' }}
              rowClassName={(record) => selectedCurve?.uuid === record.uuid ? 'row-selected' : ''}
              onRow={(record) => ({
                onClick: () => handleSelectCurve(record),
                style: { cursor: 'pointer' }
              })}
            />
          </Card>
        </Col>

        {/* 中间分隔 */}
        <Col span={1} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: 1, height: '80%', background: '#d9d9d9' }} />
        </Col>

        {/* 右侧：曲线点定义 */}
        <Col span={13} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Card
            title={
              <span>
                曲线点定义
                {selectedCurve && <Tag color="green" style={{ marginLeft: 8 }}>{selectedCurve.curve_name}</Tag>}
              </span>
            }
            extra={
              selectedCurve ? (
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAddPoint}>新增曲线点</Button>
              ) : null
            }
            bodyStyle={{ padding: 0, flex: 1, overflow: 'auto' }}
            style={{ height: '100%' }}
          >
            {selectedCurve ? (
              <Table
                columns={pointColumns}
                dataSource={points}
                rowKey="id"
                size="small"
                pagination={false}
                scroll={{ y: 'calc(100vh - 220px)' }}
              />
            ) : (
              <div style={{ padding: 100, textAlign: 'center', color: '#999' }}>
                <LeftOutlined style={{ fontSize: 24, marginRight: 8 }} />
                请选择左侧曲线查看曲线点
                <RightOutlined style={{ fontSize: 24, marginLeft: 8 }} />
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 曲线定义弹窗 */}
      <Modal
        title={editingDef ? '编辑曲线定义' : '新增曲线定义'}
        open={defModalVisible}
        onOk={handleSaveDef}
        onCancel={() => setDefModalVisible(false)}
        width={500}
      >
        <Form form={defForm} layout="vertical">
          <Form.Item name="curve_code" label="曲线代码" rules={[{ required: true }]}>
            <Input placeholder="如: SHIBOR, GOV_BOND_1Y" />
          </Form.Item>
          <Form.Item name="curve_name" label="曲线名称" rules={[{ required: true }]}>
            <Input placeholder="如: 上海银行间同业拆借利率" />
          </Form.Item>
          <Form.Item name="curve_type" label="曲线类型">
            <Select placeholder="选择曲线类型" options={curveTypeOptions.length > 0 ? curveTypeOptions : [
              { value: 'SHIBOR', label: 'SHIBOR' },
              { value: '国债', label: '国债' },
              { value: 'LPR', label: 'LPR' },
              { value: 'FTP', label: 'FTP' },
              { value: '存贷', label: '存贷' },
              { value: '其他', label: '其他' }
            ]} />
          </Form.Item>
          <Form.Item name="currency" label="币种" initialValue="CNY">
            <Select options={[
              { value: 'CNY', label: '人民币' },
              { value: 'USD', label: '美元' },
              { value: 'EUR', label: '欧元' },
              { value: 'HKD', label: '港币' }
            ]} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="曲线描述信息" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="其他备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 曲线点弹窗 */}
      <Modal
        title={editingPoint ? '编辑曲线点' : '新增曲线点'}
        open={pointModalVisible}
        onOk={handleSavePoint}
        onCancel={() => setPointModalVisible(false)}
        width={450}
      >
        <Form form={pointForm} layout="vertical">
          <Form.Item name="term" label="期限" rules={[{ required: true }]}>
            <Select placeholder="选择期限" options={[
              { value: '1D', label: '1天 (1D)' },
              { value: '7D', label: '7天 (7D)' },
              { value: '1W', label: '1周 (1W)' },
              { value: '2W', label: '2周 (2W)' },
              { value: '1M', label: '1个月 (1M)' },
              { value: '2M', label: '2个月 (2M)' },
              { value: '3M', label: '3个月 (3M)' },
              { value: '6M', label: '6个月 (6M)' },
              { value: '9M', label: '9个月 (9M)' },
              { value: '1Y', label: '1年 (1Y)' },
              { value: '2Y', label: '2年 (2Y)' },
              { value: '3Y', label: '3年 (3Y)' },
              { value: '5Y', label: '5年 (5Y)' },
              { value: '7Y', label: '7年 (7Y)' },
              { value: '10Y', label: '10年 (10Y)' },
              { value: '15Y', label: '15年 (15Y)' },
              { value: '20Y', label: '20年 (20Y)' },
              { value: '30Y', label: '30年 (30Y)' }
            ]} />
          </Form.Item>
          <Form.Item name="rate_value" label="利率值(小数形式)">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="如: 0.0325 表示 3.25%"
              step={0.0001}
              min={0}
              max={1}
              precision={6}
            />
          </Form.Item>
          <Form.Item name="spread" label="利差(基点)">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="如: 50 表示 50BP"
              step={1}
            />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CurvePage
