import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, InputNumber, Space, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, BookOutlined, TagsOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

const DictPage = () => {
  const [dicts, setDicts] = useState<any[]>([])
  const [activeDict, setActiveDict] = useState<string>('')
  const [values, setValues] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  // 弹窗
  const [modalVisible, setModalVisible] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [form] = Form.useForm()

  const fetchDicts = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/basic-param/dict')
      setDicts(Array.isArray(res.data) ? res.data : [])
      if (!activeDict && res.data.length) {
        setActiveDict(res.data[0].dict_id)
      }
    } catch (e) { message.error('加载字典失败') }
    finally { setLoading(false) }
  }

  const fetchValues = async (dictId: string) => {
    try {
      const res = await apiClient.get(`/basic-param/dict/${dictId}/values`)
      setValues(Array.isArray(res.data) ? res.data : [])
    } catch (e) { message.error('加载字典值失败') }
  }

  useEffect(() => {
    fetchDicts()
  }, [])

  useEffect(() => {
    if (activeDict) {
      fetchValues(activeDict)
    }
  }, [activeDict])

  const handleAdd = () => {
    setEditingItem(null)
    form.resetFields()
    form.setFieldsValue({ dict_id: activeDict, sort_no: values.length + 1 })
    setModalVisible(true)
  }

  const handleEdit = (item: any) => {
    setEditingItem(item)
    form.setFieldsValue(item)
    setModalVisible(true)
  }

  const handleDelete = async (item: any) => {
    try {
      await apiClient.delete(`/basic-param/dict/value/${item.id}`)
      message.success('删除成功')
      fetchValues(activeDict)
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const formData = await form.validateFields()
      if (editingItem) {
        await apiClient.put(`/basic-param/dict/value/${editingItem.id}`, formData)
        message.success('更新成功')
      } else {
        await apiClient.post(`/basic-param/dict/${activeDict}/values`, formData)
        message.success('新增成功')
      }
      setModalVisible(false)
      fetchValues(activeDict)
    } catch (e: any) {
      message.error('操作失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  // ===== 字典值列 =====
  const valueColumns = [
    { title: '排序', dataIndex: 'sort_no', key: 'sort_no', width: 80 },
    {
      title: '码值',
      dataIndex: 'value_code',
      key: 'value_code',
      width: 150,
      render: (val: string) => <span style={{ fontFamily: 'monospace', color: '#1890ff', fontWeight: 'bold' }}>{val}</span>
    },
    { title: '名称', dataIndex: 'value_name', key: 'value_name', ellipsis: true },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          <Popconfirm title="确认删除该字典值?" onConfirm={() => handleDelete(r)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  const filteredValues = values.filter(v =>
    !search ||
    (v.value_code || '').toLowerCase().includes(search.toLowerCase()) ||
    (v.value_name || '').includes(search)
  )

  const activeDictInfo = dicts.find(d => d.dict_id === activeDict)

  return (
    <div>
      <h2>数据字典</h2>

      <div style={{ display: 'flex', gap: 16 }}>
        {/* 左侧：字典列表 */}
        <Card
          title={<span><BookOutlined /> 字典列表 ({dicts.length})</span>}
          style={{ width: 400, flexShrink: 0 }}
          extra={
            <Button type="link" icon={<ReloadOutlined />} onClick={fetchDicts}>刷新</Button>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {dicts.map(d => (
              <div
                key={d.dict_id}
                onClick={() => setActiveDict(d.dict_id)}
                style={{
                  padding: '12px 16px',
                  border: '1px solid #f0f0f0',
                  borderRadius: 4,
                  cursor: 'pointer',
                  background: activeDict === d.dict_id ? '#e6f7ff' : '#fff',
                  borderColor: activeDict === d.dict_id ? '#1890ff' : '#f0f0f0'
                }}
              >
                <div style={{ fontWeight: 'bold', color: '#1890ff' }}>{d.dict_id}</div>
                <div style={{ marginTop: 4 }}>{d.dict_name}</div>
                <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>{d.description}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* 右侧：字典值列表 */}
        <Card
          style={{ flex: 1 }}
          title={
            <span>
              <TagsOutlined /> {activeDictInfo?.dict_name || '字典码值'} ({filteredValues.length})
            </span>
          }
          extra={
            <Space>
              <Input.Search
                placeholder="搜索码值/名称"
                allowClear
                style={{ width: 240 }}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Button icon={<ReloadOutlined />} onClick={() => fetchValues(activeDict)}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} disabled={!activeDict}>新增</Button>
            </Space>
          }
        >
          <Table
            columns={valueColumns}
            dataSource={filteredValues}
            rowKey="id"
            loading={loading}
            size="small"
            scroll={{ y: 500 }}
            pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
            bordered
          />
        </Card>
      </div>

      <Modal
        title={editingItem ? '编辑字典值' : '新增字典值'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="dict_id" label="字典ID">
            <Input disabled />
          </Form.Item>
          <Form.Item name="value_code" label="码值" rules={[{ required: true, max: 6 }]}>
            <Input placeholder="如 NUM001（限6位以内）" />
          </Form.Item>
          <Form.Item name="value_name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如 生息资产" />
          </Form.Item>
          <Form.Item name="sort_no" label="排序">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DictPage